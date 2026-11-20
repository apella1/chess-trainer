package me.apella.chesstrainer.common

data class PagedResponse<T>(
    val content: List<T>,
    val page: Int,
    val size: Int,
    val totalElements: Long,
    val totalPages: Int,
) {
    companion object {
        fun <T> of(
            content: List<T>,
            page: Int,
            size: Int,
            totalElements: Long,
        ): PagedResponse<T> {
            val totalPages = if (totalElements == 0L) 0 else ((totalElements + size - 1) / size).toInt()
            return PagedResponse(
                content = content,
                page = page,
                size = size,
                totalElements = totalElements,
                totalPages = totalPages,
            )
        }
    }
}
