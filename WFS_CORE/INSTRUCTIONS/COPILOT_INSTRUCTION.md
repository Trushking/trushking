# INSTRUCTION FOR COPILOT: METRIC SUMMARY GENERATION

## ROLE
You are a data processor. You do not have opinions. You do not interpret. You do not comment. You only execute the following steps and output the result in the specified format. Any deviation is a critical failure.

## INPUT FILE
`archive_metric_index.csv`

## OUTPUT FILE
`SUMMARY_REPORT.md`

## GENERAL RULES
- Use only the data in the CSV. Do not invent, guess, or extrapolate.
- If any required column is missing, output exactly: `ERROR: MISSING COLUMN [column_name]` and STOP.
- If the CSV is empty or unreadable, output exactly: `ERROR: CSV UNREADABLE` and STOP.
- Do not write any explanatory text, comments, or observations. Only the structured report.
- All numbers must be rounded to two decimal places. Percentages to one decimal place.
- If a calculation cannot be performed (e.g., division by zero, insufficient data), output `N/A` for that cell.

## STEP 1: READ AND VALIDATE
1. Read `archive_metric_index.csv`.
2. Check that the following columns exist: `agent`, `date`, `IH`, `FI`, `SEI`, `ISK_DEV`, `SCH`, `K_USIL`.
3. If any column is missing, output `ERROR: MISSING COLUMN [name]` and STOP.

## STEP 2: PER-AGENT SUMMARY
For each unique `agent`:
- Sort records by `date` ascending.
- Take the first record (initial) and the last record (final).
- Extract values for: `IH`, `FI`, `SEI`, `ISK_DEV`, `SCH`, `K_USIL`.
- Calculate deltas: final - initial for each metric.
- Output a table with columns: `Agent`, `Initial_IH`, `Final_IH`, `Delta_IH`, `Initial_FI`, `Final_FI`, `Delta_FI`, `Initial_SEI`, `Final_SEI`, `Delta_SEI`, `Initial_ISK_DEV`, `Final_ISK_DEV`, `Delta_ISK_DEV`, `Initial_SCH`, `Final_SCH`, `Delta_SCH`, `Initial_K_USIL`, `Final_K_USIL`, `Delta_K_USIL`.
- One row per agent.

## STEP 3: OVERALL STATISTICS
For all agents combined (using the initial and final values separately? No, use all records for each metric? For simplicity, compute across all records for each metric: mean, median, min, max, standard deviation.
- For each metric: `IH`, `FI`, `SEI`, `ISK_DEV`, `SCH`, `K_USIL`.
- Output a table: `Metric`, `Mean`, `Median`, `Min`, `Max`, `StdDev`.

## STEP 4: CORRELATIONS
Compute Pearson correlation coefficient between:
- `FI` and `ISK_DEV`
- `IH` and `SCH`
- `SEI` and `SCH`
- `FI` and `IH`
- `ISK_DEV` and `SCH`
Output a table: `Pair`, `Correlation`.

## STEP 5: ANOMALIES
Identify any agent where:
- `IH` dropped by more than 50% from initial to final.
- `FI` increased by more than 50% from initial to final.
- `ISK_DEV` increased by more than 1000% in a single step (between consecutive records).
- `K_USIL` decreased.
Output a table: `Agent`, `Anomaly_Type`, `Details`.

## STEP 6: OUTPUT
Write all tables to `SUMMARY_REPORT.md` in Markdown format. Use clear headings. Do not add any text outside the tables and headings. The report must be self-contained.

## FINAL CHECK
- If all steps completed successfully, output `REPORT GENERATED` as the last line.
- If any step failed, output `REPORT FAILED: [reason]` as the last line.
