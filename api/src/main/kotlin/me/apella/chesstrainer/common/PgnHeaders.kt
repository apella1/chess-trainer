package me.apella.chesstrainer.common

/**
 * Simple PGN header parser.
 *
 * Extracts tag-value pairs from the header section of a PGN game.
 * PGN headers have the format: [Key "Value"]
 *
 * Does not parse movetext — that is done client-side by chess.js in the UI.
 */
object PgnHeaders {

    private val HEADER_PATTERN = Regex("""^\[(\w+)\s+"(.*)"\]\s*$""")

    /**
     * Parse all headers from a PGN string.
     * Returns a map of tag name to tag value.
     */
    fun parse(pgn: String): Map<String, String> {
        val headers = mutableMapOf<String, String>()
        for (line in pgn.lines()) {
            val trimmed = line.trim()
            if (trimmed.isEmpty()) {
                // First empty line marks the end of headers and start of movetext
                if (headers.isNotEmpty()) break
                continue
            }
            val match = HEADER_PATTERN.matchEntire(trimmed)
            if (match != null) {
                headers[match.groupValues[1]] = match.groupValues[2]
            } else if (headers.isNotEmpty()) {
                // We've passed the header section
                break
            }
        }
        return headers
    }

    /**
     * Extract a single header value, or null if not present.
     */
    fun get(pgn: String, key: String): String? = parse(pgn)[key]

    /**
     * Split a multi-game PGN file into individual game strings.
     * Games are separated by the start of a new [Event "..."] header.
     */
    fun splitGames(pgnText: String): List<String> {
        val games = mutableListOf<String>()
        val current = StringBuilder()

        for (line in pgnText.lines()) {
            val trimmed = line.trim()
            if (trimmed.startsWith("[Event ") && current.isNotEmpty()) {
                games.add(current.toString().trim())
                current.clear()
            }
            current.append(line).append("\n")
        }

        if (current.isNotBlank()) {
            games.add(current.toString().trim())
        }

        return games.filter { it.isNotBlank() }
    }

    /**
     * Derive the opening name from headers.
     * Tries [Opening] first, then parses from [ECOUrl] if available.
     */
    fun openingName(headers: Map<String, String>): String? {
        headers["Opening"]?.let { return it }
        headers["ECOUrl"]?.let { url ->
            // Extract the last path segment and replace dashes with spaces
            val segment = url.trimEnd('/').substringAfterLast('/')
            return segment.replace("-", " ")
        }
        return null
    }
}
