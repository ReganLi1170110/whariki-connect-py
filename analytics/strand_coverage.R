#!/usr/bin/env Rscript
# Bar chart of published Learning Stories per Te Whariki strand.
#
# Usage:
#   Rscript strand_coverage.R <input_csv> <output_png> <title>
#
# input_csv must have exactly two columns: strand,count
# This script is called from Flask via subprocess (see app/analytics_routes.py);
# it is written to also run standalone for testing, per the project's
# risk-mitigation plan of verifying the R step in isolation first.

suppressPackageStartupMessages(library(ggplot2))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: Rscript strand_coverage.R <input_csv> <output_png> [title]")
}

input_csv  <- args[1]
output_png <- args[2]
chart_title <- if (length(args) >= 3) args[3] else "Learning stories per Te Whariki strand"

data <- read.csv(input_csv, stringsAsFactors = FALSE)
if (!all(c("strand", "count") %in% names(data))) {
  stop("Input CSV must have 'strand' and 'count' columns.")
}

# Canonical Te Whariki strand order, so the chart reads the same way every
# time rather than sorting alphabetically or by count.
strand_order <- c("Wellbeing", "Belonging", "Contribution", "Communication", "Exploration")
data$strand <- factor(data$strand, levels = strand_order)
data <- data[!is.na(data$strand), ]

# Brand colours, matching the rest of the platform.
BRAND_GREEN <- "#1F3D2E"
BRAND_GOLD  <- "#E3A730"
INK_SOFT    <- "#52685A"

chart <- ggplot(data, aes(x = strand, y = count)) +
  geom_col(fill = BRAND_GREEN, width = 0.62) +
  geom_text(aes(label = count), vjust = -0.6, size = 4.2, colour = BRAND_GREEN, fontface = "bold") +
  labs(title = chart_title, x = NULL, y = "Published learning stories") +
  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(face = "bold", colour = BRAND_GREEN, size = 15, margin = margin(b = 12)),
    axis.text = element_text(colour = INK_SOFT),
    axis.title.y = element_text(colour = INK_SOFT, margin = margin(r = 8)),
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_blank(),
    plot.background = element_rect(fill = "white", colour = NA)
  ) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.15)))

ggsave(output_png, chart, width = 8, height = 4.5, dpi = 130, bg = "white")
cat("Chart written to", output_png, "\n")
