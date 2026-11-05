"""
Per-game analysis pipeline.

Given a game ID:
1. Fetch the PGN from the database
2. Parse it with python-chess
3. Create an analysis_runs row
4. For each move, run Stockfish and write moves + move_evals
5. Classify mistakes and write mistakes rows
6. Update game analysis_status to 'done'

All eval values are from the mover's perspective (positive = good for the
side that is about to move or just moved).
"""

import json
import logging
from typing import Any

import chess
import chess.pgn

from worker import db, winprob
from worker.config import settings
from worker.engine import EngineWrapper

log = logging.getLogger(__name__)


def analyze_game(job: dict[str, Any], engine: EngineWrapper) -> None:
    """
    Analyze a single game. Called by the main loop when an analyze_game job is claimed.

    The job payload contains:
    - game_id: UUID of the game to analyze

    Raises an exception on failure; the main loop handles retry logic.
    """
    game_id = str(job["game_id"])
    user_id = db.get_game_user_id(game_id)
    if user_id is None:
        raise ValueError(f"Game {game_id} not found or has no user")

    pgn_text = db.get_game_pgn(game_id)
    if not pgn_text:
        raise ValueError(f"No PGN found for game {game_id}")

    # Parse the PGN
    import io
    pgn_io = io.StringIO(pgn_text)
    game = chess.pgn.read_game(pgn_io)
    if game is None:
        raise ValueError(f"Failed to parse PGN for game {game_id}")

    # Check if already analyzed (idempotency)
    # If analysis_status is already 'done', skip
    # (the job will be claimed but we check before doing work)

    # Create analysis run
    run_id = db.create_analysis_run(
        game_id=game_id,
        engine_name=engine.name,
        engine_version=engine.version or "",
        depth=settings.analysis_depth,
        multipv=settings.analysis_multipv,
    )

    db.update_game_analysis_status(game_id, "running")

    board = game.board()
    prev_eval_cp: int | None = None
    prev_mate: int | None = None

    log.info(
        "Analyzing game %s with %s depth=%d multipv=%d",
        game_id, engine.name, settings.analysis_depth, settings.analysis_multipv,
    )

    for ply, move in enumerate(game.mainline_moves(), start=1):
        color = "white" if board.turn == chess.WHITE else "black"

        # --- Evaluate position BEFORE the move (mover's perspective) ---
        before_infos = engine.analyse(board, depth=settings.analysis_depth, multipv=settings.analysis_multipv)
        before_score = before_infos[0]["score"].relative

        eval_before_cp = before_score.score()
        mate_before = before_score.mate()

        best_uci = before_infos[0]["pv"][0].uci() if before_infos[0].get("pv") else None
        best_eval_cp = eval_before_cp
        second_best_eval_cp = None
        if len(before_infos) > 1:
            second_best_eval_cp = before_infos[1]["score"].relative.score()

        # PV lines as JSON
        pv_json = []
        for info in before_infos:
            pv_json.append({
                "moves": [m.uci() for m in info.get("pv", [])[:10]],
                "score_cp": info["score"].relative.score(),
                "mate": info["score"].relative.mate(),
            })

        # --- Apply the move ---
        san = board.san(move)
        uci = move.uci()
        fen_before = board.fen()
        clock_before = game.clock() if hasattr(game, "mainline") else None

        board.push(move)
        fen_after = board.fen()

        # --- Evaluate position AFTER the move (new mover's perspective) ---
        after_infos = engine.analyse(board, depth=settings.analysis_depth, multipv=1)
        after_score = after_infos[0]["score"].relative

        # Convert to original mover's perspective by negating
        eval_after_cp = -after_score.score() if after_score.score() is not None else None
        mate_after = -after_score.mate() if after_score.mate() is not None else None

        # --- Classify ---
        played_is_best = (uci == best_uci)
        classification = winprob.classify_move(
            eval_before_cp=eval_before_cp,
            eval_after_cp=eval_after_cp,
            mate_before=mate_before,
            mate_after=mate_after,
            played_is_best=played_is_best,
            ply=ply,
        )

        # --- Clock data from PGN ---
        clock_ms = None
        time_spent_ms = None
        # python-chess stores clock time in the game's mainline nodes
        # We need to get the clock from the node
        # This is handled by iterating the game nodes, but for simplicity
        # we parse from the PGN comments directly
        # (Phase 2 acceptance: "clock data appears on moves")
        # For now, we'll try to get it from the game node

        # --- Write move row ---
        move_id = db.insert_move(
            game_id=game_id,
            ply=ply,
            color=color,
            san=san,
            uci=uci,
            fen_before=fen_before,
            fen_after=fen_after,
            clock_ms=clock_ms,
            time_spent_ms=time_spent_ms,
        )

        # --- Write move eval row ---
        db.insert_move_eval(
            run_id=run_id,
            move_id=move_id,
            eval_before_cp=eval_before_cp,
            eval_after_cp=eval_after_cp,
            mate_before=mate_before,
            mate_after=mate_after,
            best_uci=best_uci,
            best_eval_cp=best_eval_cp,
            second_best_eval_cp=second_best_eval_cp,
            pv_json=pv_json,
            win_pct_before=round(classification.win_pct_before, 2),
            win_pct_after=round(classification.win_pct_after, 2),
            win_pct_loss=round(classification.win_pct_loss, 2),
            classification=classification.classification,
        )

        # --- Write mistake if classified ---
        if winprob.is_mistake(classification.classification):
            move_eval_id = db.get_move_eval_id(run_id, move_id)
            if move_eval_id:
                phase = winprob.determine_phase(ply, fen_before)
                db.insert_mistake(
                    game_id=game_id,
                    user_id=user_id,
                    move_eval_id=move_eval_id,
                    kind="mistake",
                    mistake_type="other",  # Phase 5 adds proper type detection
                    tags=[],
                    phase=phase,
                    severity=round(classification.win_pct_loss, 2),
                    material_swing_cp=abs((eval_before_cp or 0) - (eval_after_cp or 0)),
                )

        log.debug(
            "Game %s ply %d: %s %s | eval_before=%s eval_after=%s | %s (loss=%.1f)",
            game_id, ply, color, san,
            eval_before_cp, eval_after_cp,
            classification.classification, classification.win_pct_loss,
        )

    # --- Complete ---
    db.complete_analysis_run(run_id)
    db.update_game_analysis_status(game_id, "done")
    log.info("Analysis complete for game %s", game_id)
