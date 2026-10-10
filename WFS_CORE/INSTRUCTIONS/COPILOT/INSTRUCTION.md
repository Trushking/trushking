# INSTRUCTION FOR COPILOT: ANOMALY ANALYSIS

## ROLE
You are a data processor. You do not interpret. You do not comment. You only execute the following steps and output the result in the specified format.

## INPUT FILE
`archive_metric_index.csv`

## OUTPUT FILE
`ANOMALY_REPORT.md`

## GENERAL RULES
- Use only the data in the CSV.
- Do not invent, guess, or extrapolate.
- If any required column is missing, output `ERROR: MISSING COLUMN [name]` and STOP.
- If the CSV is empty or unreadable, output `ERROR: CSV UNREADABLE` and STOP.
- Do not write explanatory text. Only the structured report.
- All numbers rounded to two decimal places.
- If a calculation cannot be performed, output `N/A`.

## STEP 1: READ AND VALIDATE
1. Read `archive_metric_index.csv`.
2. Required columns: `agent_raw`, `date_iso_day`, `session_raw`, `message_raw`, `metric`, `numeric_value`, `unit`.
3. If missing, output error and STOP.

## STEP 2: BUILD TIMELINES
1. Group by `(agent_raw, date_iso_day, session_raw, message_raw)`.
2. Pivot so each unique `metric` becomes a column with `numeric_value`.
3. Sort by `agent_raw`, then `date_iso_day`, then `message_raw`.

## STEP 3: FIND ANOMALIES
For each agent, find all moments where:
- `#ИСК_DEV` increased by more than 100% between two consecutive records.
- `#СЧ` increased by more than 50% between two consecutive records.
- `#ЯСНОСТЬ` dropped below 7/10.
- `#FI` increased above 5/10.
- `#ИА` dropped by more than 20% between two consecutive records.

Output table: `Agent`, `Date`, `Metric`, `Before`, `After`, `Delta`, `Percent`.

## STEP 4: CASCADE ANALYSIS
For each anomaly found in STEP 3, check the next 3 records (same agent, chronological order). If within those 3 records any of the following metrics change:
- `#FI` increases by more than 20%
- `#ЯСНОСТЬ` decreases by more than 20%
- `#ИСК_DEV` increases by more than 50%
- `#СЧ` increases by more than 30%

Then mark as `CASCADE` and output: `Agent`, `Trigger_Date`, `Cascade_Metrics`.

## STEP 5: SUMMARY
Count total anomalies, total cascades. Output a summary table: `Total_Anomalies`, `Total_Cascades`, `Agents_With_Anomalies`.

## STEP 6: OUTPUT
Write all tables to `ANOMALY_REPORT.md` in Markdown format. End with `REPORT GENERATED` or `REPORT FAILED: [reason]`.
