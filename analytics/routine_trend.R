#!/usr/bin/env Rscript
# Line chart of one child's weekly meal score and toileting issue rate.
#
# Usage: Rscript routine_trend.R <input_csv> <output_png> <title>
# input_csv columns: week_start,meal_score,toileting_issue_pct
#
# meal_score: weekly average of (All=100, Most=66, Some=33, None=0), so it
# reads as "how well is this child eating", 0-100.
# toileting_issue_pct: % of that week's toileting events that were an
# Accident or a Soiled nappy, i.e. the ones a teacher would want to know
# about, also 0-100 so both lines share one axis.

suppressPackageStartupMessages(library(ggplot2))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) stop("Usage: Rscript routine_trend.R <input_csv> <output_png> [title]")

input_csv  <- args[1]
output_png <- args[2]
chart_title <- if (length(args) >= 3) args[3] else "Weekly routine trends"

data <- read.csv(input_csv, stringsAsFactors = FALSE)
if (!all(c("week_start", "meal_score", "toileting_issue_pct") %in% names(data))) {
  stop("Input CSV must have 'week_start', 'meal_score' and 'toileting_issue_pct' columns.")
}
data$week_start <- as.Date(data$week_start)

# Reshape to long format so both lines can share one legend.
long_data <- data.frame(
  week_start = rep(data$week_start, 2),
  value = c(data$meal_score, data$toileting_issue_pct),
  series = rep(c("Meals eaten (score)", "Toileting issues (%)"), each = nrow(data))
)

BRAND_GREEN <- "#1F3D2E"
BRAND_ALERT <- "#B85C42"
INK_SOFT    <- "#52685A"

chart <- ggplot(long_data, aes(x = week_start, y = value, colour = series)) +
  geom_line(linewidth = 1.1) +
  geom_point(size = 2.6) +
  scale_colour_manual(values = c("Meals eaten (score)" = BRAND_GREEN,
                                  "Toileting issues (%)" = BRAND_ALERT)) +
  labs(title = chart_title, x = NULL, y = NULL, colour = NULL) +
  scale_y_continuous(limits = c(0, 100), expand = expansion(mult = c(0.02, 0.08))) +
  scale_x_date(date_labels = "%d %b") +
  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(face = "bold", colour = BRAND_GREEN, size = 15, margin = margin(b = 12)),
    axis.text = element_text(colour = INK_SOFT),
    panel.grid.minor = element_blank(),
    legend.position = "top",
    legend.justification = "left",
    legend.text = element_text(colour = INK_SOFT, size = 11),
    plot.background = element_rect(fill = "white", colour = NA)
  )

ggsave(output_png, chart, width = 8, height = 4.7, dpi = 130, bg = "white")
cat("Chart written to", output_png, "\n")
