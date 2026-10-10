#!/usr/bin/env Rscript
# Line chart of weekly attendance rate (% present) over time.
#
# Usage: Rscript attendance_trend.R <input_csv> <output_png> <title>
# input_csv columns: week_start,present_pct

suppressPackageStartupMessages(library(ggplot2))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) stop("Usage: Rscript attendance_trend.R <input_csv> <output_png> [title]")

input_csv  <- args[1]
output_png <- args[2]
chart_title <- if (length(args) >= 3) args[3] else "Weekly attendance rate"

data <- read.csv(input_csv, stringsAsFactors = FALSE)
if (!all(c("week_start", "present_pct") %in% names(data))) {
  stop("Input CSV must have 'week_start' and 'present_pct' columns.")
}
data$week_start <- as.Date(data$week_start)

BRAND_GREEN <- "#1F3D2E"
BRAND_GOLD  <- "#E3A730"
INK_SOFT    <- "#52685A"

chart <- ggplot(data, aes(x = week_start, y = present_pct)) +
  geom_line(colour = BRAND_GREEN, linewidth = 1.1) +
  geom_point(colour = BRAND_GOLD, size = 3) +
  labs(title = chart_title, x = NULL, y = "Present (%)") +
  scale_y_continuous(limits = c(0, 100), expand = expansion(mult = c(0.02, 0.08))) +
  scale_x_date(date_labels = "%d %b") +
  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(face = "bold", colour = BRAND_GREEN, size = 15, margin = margin(b = 12)),
    axis.text = element_text(colour = INK_SOFT),
    axis.title.y = element_text(colour = INK_SOFT, margin = margin(r = 8)),
    panel.grid.minor = element_blank(),
    plot.background = element_rect(fill = "white", colour = NA)
  )

ggsave(output_png, chart, width = 8, height = 4.5, dpi = 130, bg = "white")
cat("Chart written to", output_png, "\n")
