package me.apella.chesstrainer.games

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.GeneratedValue
import jakarta.persistence.GenerationType
import jakarta.persistence.Id
import jakarta.persistence.Table
import java.util.UUID

@Entity
@Table(name = "moves")
class MoveEntity(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    val id: UUID? = null,
    @Column(name = "game_id", nullable = false)
    val gameId: UUID,
    @Column(nullable = false)
    val ply: Int,
    @Column(nullable = false)
    val color: String,
    @Column(nullable = false)
    val san: String,
    val uci: String? = null,
    @Column(name = "fen_before", nullable = false)
    val fenBefore: String,
    @Column(name = "fen_after", nullable = false)
    val fenAfter: String,
    @Column(name = "clock_ms_remaining")
    val clockMsRemaining: Long? = null,
    @Column(name = "time_spent_ms")
    val timeSpentMs: Long? = null,
)

@Entity
@Table(name = "move_evals")
class MoveEvalEntity(
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    val id: UUID? = null,
    @Column(name = "run_id", nullable = false)
    val runId: UUID,
    @Column(name = "move_id", nullable = false)
    val moveId: UUID,
    @Column(name = "eval_before_cp")
    val evalBeforeCp: Int? = null,
    @Column(name = "eval_after_cp")
    val evalAfterCp: Int? = null,
    @Column(name = "mate_before")
    val mateBefore: Int? = null,
    @Column(name = "mate_after")
    val mateAfter: Int? = null,
    @Column(name = "best_uci")
    val bestUci: String? = null,
    @Column(name = "best_eval_cp")
    val bestEvalCp: Int? = null,
    @Column(name = "second_best_eval_cp")
    val secondBestEvalCp: Int? = null,
    @Column(name = "win_pct_before")
    val winPctBefore: Double? = null,
    @Column(name = "win_pct_after")
    val winPctAfter: Double? = null,
    @Column(name = "win_pct_loss")
    val winPctLoss: Double? = null,
    val classification: String? = null,
)
