"""
Entry templates for Research Logger.
"""
from datetime import date


def daily_template(entry_date: str = None) -> str:
    if entry_date is None:
        entry_date = date.today().isoformat()

    # Format as readable date
    try:
        from datetime import datetime
        d = datetime.strptime(entry_date, "%Y-%m-%d")
        readable = d.strftime("%A, %B %d, %Y")
    except Exception:
        readable = entry_date

    return f"""<h1>Research Log — {readable}</h1>
<p></p>
<h2>What I Worked On Today</h2>
<p></p>
<h2>Experiments / Results</h2>
<p></p>
<h2>Problems Encountered</h2>
<p></p>
<h2>Ideas / Observations</h2>
<p></p>
<h2>Plan for Tomorrow</h2>
<p></p>
<hr>
<p><em>Tags:</em> </p>
"""


def weekly_summary_template(start_date: str, end_date: str) -> str:
    return f"""# Weekly Summary
**Period:** {start_date} → {end_date}

## Key Accomplishments

## Main Experiments & Results

## Recurring Problems / Themes

## Top Ideas This Week

## Next Week Priorities

---
*Auto-generated summary*
"""


def monthly_summary_template(year: int, month: int) -> str:
    import calendar
    month_name = calendar.month_name[month]
    return f"""# Monthly Summary — {month_name} {year}

## Highlights

## Completed Work

## Ongoing Projects

## Key Learnings

## Goals for Next Month

---
*Auto-generated summary*
"""
