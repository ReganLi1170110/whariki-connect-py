#!/usr/bin/env Rscript
# Bar chart of accident forms by injury type, most common first.
#
# Usage: Rscript accident_frequency.R <input_csv> <output_png> <title>
# input_csv columns: nature,count

suppressPackageStartupMessages(library(ggplot2))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) stop("Usage: Rscript accident_frequency.R <input_csv> <output_png> [title]")

input_csv  <- args[1]
output_png <- args[2]
chart_title <- if (length(args) >= 3) args[3] else "Accident frequency by injury type"

data <- read.csv(input_csv, stringsAsFactors = FALSE)
if (!all(c("nature", "count") %in% names(data))) {
  stop("Input CSV must have 'nature' and 'count' columns.")
}
# No forms in the selected range: draw a labelled empty chart instead of
# failing on max() of an empty column. The analytics page already shows an
# empty-state message, but the PNG/download link can still be opened
# directly for a range with no accidents.
if (nrow(data) == 0) {
  empty_chart <- ggplot() +
    annotate("text", x = 0, y = 0, label = "No accident forms in this period",
             colour = "#52685A", size = 5) +
    labs(title = chart_title) +
    theme_void(base_size = 13) +
    theme(plot.title = element_text(face = "bold", colour = "#1F3D2E", size = 15),
          plot.background = element_rect(fill = "white", colour = NA))
  ggsave(output_png, empty_chart, width = 8, height = 4.5, dpi = 130, bg = "white")
  quit(save = "no", status = 0)
}

data$nature <- factor(data$nature, levels = data$nature[order(data$count)])

max_count <- max(data$count)
axis_step <- if (max_count <= 10) 1 else ceiling(max_count / 5)
integer_breaks <- seq(0, max_count, by = axis_step)

BRAND_ALERT <- "#B85C42"
INK_SOFT    <- "#52685A"
BRAND_GREEN <- "#1F3D2E"

chart <- ggplot(data, aes(x = nature, y = count)) +
  geom_col(fill = BRAND_ALERT, width = 0.62) +
  geom_text(aes(label = count), hjust = -0.4, size = 4.2, colour = BRAND_ALERT, fontface = "bold") +
  coord_flip() +
  labs(title = chart_title, x = NULL, y = "Accident forms") +
  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(face = "bold", colour = BRAND_GREEN, size = 15, margin = margin(b = 12)),
    axis.text = element_text(colour = INK_SOFT),
    axis.title.x = element_text(colour = INK_SOFT, margin = margin(t = 8)),
    panel.grid.minor = element_blank(),
    panel.grid.major.y = element_blank(),
    plot.background = element_rect(fill = "white", colour = NA)
  ) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.18)), breaks = integer_breaks)

ggsave(output_png, chart, width = 8, height = 4.5, dpi = 130, bg = "white")
cat("Chart written to", output_png, "\n")
