"""Streamlit dashboard for the CloudGuard CSPM project."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from dashboard.database import (
        DEFAULT_DATABASE_PATH,
        fetch_all_findings,
    )
except ModuleNotFoundError:
    from database import (
        DEFAULT_DATABASE_PATH,
        fetch_all_findings,
    )



PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / DEFAULT_DATABASE_PATH


st.set_page_config(
    page_title="CloudGuard CSPM Dashboard",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)


SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
SEVERITY_COLORS = {
    "CRITICAL": "#8B0000",
    "HIGH": "#D62728",
    "MEDIUM": "#FF8C00",
    "LOW": "#2CA02C",
}


@st.cache_data(ttl=30)
def load_findings() -> pd.DataFrame:
    """Load database findings into a pandas DataFrame."""
    rows = fetch_all_findings(DATABASE_PATH)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame([dict(row) for row in rows])


def calculate_posture_score(findings: pd.DataFrame) -> int:
    """
    Calculate an explainable posture score.

    Score starts at 100 and decreases according to open finding severity.
    It is a portfolio metric, not an official AWS score.
    """
    if findings.empty:
        return 100

    deductions = {
        "CRITICAL": 15,
        "HIGH": 8,
        "MEDIUM": 3,
        "LOW": 1,
    }

    deduction = sum(
        deductions.get(severity, 0)
        for severity in findings["severity"]
        if severity in deductions
    )

    return max(0, 100 - deduction)


def format_metric_delta(value: int) -> str:
    """Format a metric value with a readable sign."""
    return f"{value:+d}"


def render_metric_cards(findings: pd.DataFrame) -> None:
    """Render headline dashboard metrics."""
    if findings.empty:
        st.warning("No findings are available in the database.")
        return

    total = len(findings)
    open_count = int((findings["status"] == "OPEN").sum())
    critical_count = int((findings["severity"] == "CRITICAL").sum())
    high_count = int((findings["severity"] == "HIGH").sum())
    posture_score = calculate_posture_score(findings)

    metric_columns = st.columns(5)

    metric_columns[0].metric(
        "Total findings",
        total,
    )

    metric_columns[1].metric(
        "Open findings",
        open_count,
    )

    metric_columns[2].metric(
        "Critical",
        critical_count,
    )

    metric_columns[3].metric(
        "High",
        high_count,
    )

    metric_columns[4].metric(
        "Posture score",
        f"{posture_score}/100",
    )


def render_charts(findings: pd.DataFrame) -> None:
    """Render severity, category, and environment charts."""
    if findings.empty:
        return

    left_column, right_column = st.columns(2)

    with left_column:
        st.subheader("Findings by severity")

        severity_counts = (
            findings["severity"]
            .value_counts()
            .reindex(SEVERITY_ORDER, fill_value=0)
            .rename_axis("severity")
            .reset_index(name="count")
        )

        severity_chart = px.bar(
            severity_counts,
            x="severity",
            y="count",
            color="severity",
            category_orders={"severity": SEVERITY_ORDER},
            color_discrete_map=SEVERITY_COLORS,
            text="count",
        )

        severity_chart.update_layout(
            showlegend=False,
            xaxis_title="Severity",
            yaxis_title="Findings",
        )

        st.plotly_chart(
            severity_chart,
            use_container_width=True,
        )

    with right_column:
        st.subheader("Findings by category")

        category_counts = (
            findings["category"]
            .value_counts()
            .rename_axis("category")
            .reset_index(name="count")
        )

        category_chart = px.bar(
            category_counts,
            x="category",
            y="count",
            color="category",
            text="count",
        )

        category_chart.update_layout(
            showlegend=False,
            xaxis_title="Category",
            yaxis_title="Findings",
        )

        st.plotly_chart(
            category_chart,
            use_container_width=True,
        )

    st.subheader("Findings by environment")

    environment_counts = (
        findings["environment"]
        .value_counts()
        .rename_axis("environment")
        .reset_index(name="count")
    )

    environment_chart = px.bar(
        environment_counts,
        x="environment",
        y="count",
        color="environment",
        text="count",
    )

    environment_chart.update_layout(
        xaxis_title="Environment",
        yaxis_title="Findings",
    )

    st.plotly_chart(
        environment_chart,
        use_container_width=True,
    )


def render_filters(findings: pd.DataFrame) -> pd.DataFrame:
    """Render sidebar filters and return the filtered findings."""
    st.sidebar.header("Filters")

    environment_options = [
        "All",
        *sorted(findings["environment"].dropna().unique()),
    ]

    severity_options = [
        "All",
        *[
            severity
            for severity in SEVERITY_ORDER
            if severity in findings["severity"].unique()
        ],
    ]

    category_options = [
        "All",
        *sorted(findings["category"].dropna().unique()),
    ]

    status_options = [
        "All",
        *sorted(findings["status"].dropna().unique()),
    ]

    selected_environment = st.sidebar.selectbox(
        "Environment",
        environment_options,
    )

    selected_severity = st.sidebar.selectbox(
        "Severity",
        severity_options,
    )

    selected_category = st.sidebar.selectbox(
        "Category",
        category_options,
    )

    selected_status = st.sidebar.selectbox(
        "Status",
        status_options,
    )

    filtered = findings.copy()

    if selected_environment != "All":
        filtered = filtered[
            filtered["environment"] == selected_environment
        ]

    if selected_severity != "All":
        filtered = filtered[
            filtered["severity"] == selected_severity
        ]

    if selected_category != "All":
        filtered = filtered[
            filtered["category"] == selected_category
        ]

    if selected_status != "All":
        filtered = filtered[
            filtered["status"] == selected_status
        ]

    st.sidebar.divider()
    st.sidebar.caption(
        f"Showing {len(filtered)} of {len(findings)} findings"
    )

    return filtered


def render_findings_table(findings: pd.DataFrame) -> None:
    """Render a concise findings table."""
    st.subheader("Security findings")

    if findings.empty:
        st.info("No findings match the selected filters.")
        return

    display_columns = [
        "environment",
        "severity",
        "category",
        "risk_score",
        "check_id",
        "resource",
        "title",
        "status",
    ]

    table = findings[display_columns].copy()

    table["environment"] = table["environment"].str.title()
    table["severity"] = pd.Categorical(
        table["severity"],
        categories=SEVERITY_ORDER,
        ordered=True,
    )

    table = table.sort_values(
        by=["severity", "risk_score"],
        ascending=[True, False],
    )

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "environment": "Environment",
            "severity": "Severity",
            "category": "Category",
            "risk_score": st.column_config.NumberColumn(
                "Risk score",
                format="%d",
            ),
            "check_id": "Check ID",
            "resource": "Resource",
            "title": "Finding",
            "status": "Status",
        },
    )


def render_finding_details(findings: pd.DataFrame) -> None:
    """Render details for a selected finding."""
    if findings.empty:
        return

    st.subheader("Finding details")

    selection_labels = [
        f"{row.check_id} — {row.title}"
        for row in findings.itertuples()
    ]

    selected_label = st.selectbox(
        "Select a finding",
        selection_labels,
    )

    selected_index = selection_labels.index(selected_label)
    selected = findings.iloc[selected_index]

    detail_left, detail_right = st.columns(2)

    with detail_left:
        st.markdown(f"**Check ID:** `{selected['check_id']}`")
        st.markdown(f"**Title:** {selected['title']}")
        st.markdown(f"**Severity:** `{selected['severity']}`")
        st.markdown(f"**Category:** `{selected['category']}`")
        st.markdown(f"**Risk score:** `{selected['risk_score']}`")
        st.markdown(f"**Status:** `{selected['status']}`")

    with detail_right:
        st.markdown(f"**Environment:** `{selected['environment']}`")
        st.markdown(f"**Resource:** `{selected['resource']}`")
        st.markdown(f"**File:** `{selected['file_path']}`")
        st.markdown(f"**Line:** `{selected['line']}`")
        st.markdown(f"**Scanner:** `{selected['scanner']}`")

    st.markdown("**Description**")
    st.write(selected["description"])

    st.markdown("**Recommendation**")
    st.info(selected["recommendation"])


def render_comparison(findings: pd.DataFrame) -> None:
    """Render insecure versus remediated comparison."""
    st.subheader("Insecure versus remediated comparison")

    comparison = (
        findings.groupby(["environment", "severity"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=SEVERITY_ORDER, fill_value=0)
        .reindex(["insecure", "remediated"], fill_value=0)
    )

    comparison["Total"] = comparison.sum(axis=1)

    if "insecure" in comparison.index and "remediated" in comparison.index:
        insecure_total = int(comparison["Total"].get("insecure", 0))
        remediated_total = int(comparison["Total"].get("remediated", 0))
        reduction = insecure_total - remediated_total

        comparison_left, comparison_right = st.columns(2)

        with comparison_left:
            st.metric(
                "Failed findings reduced",
                reduction,
                delta=format_metric_delta(reduction),
            )

        with comparison_right:
            st.metric(
                "Remediated finding count",
                remediated_total,
                delta=format_metric_delta(
                    remediated_total - insecure_total
                ),
            )

    st.dataframe(
        comparison,
        use_container_width=True,
    )


def main() -> None:
    """Render the Streamlit application."""
    st.title("CloudGuard CSPM Dashboard")
    st.caption(
        "Local cloud security posture analysis for Terraform infrastructure"
    )

    if not DATABASE_PATH.exists():
        st.error(
            "Database not found. Seed the database before launching the dashboard."
        )
        st.code(
            "python .\\dashboard\\seed_database.py "
            "--input .\\data\\normalized\\insecure-findings.json "
            "--environment insecure"
        )
        st.stop()

    all_findings = load_findings()

    if all_findings.empty:
        st.warning("The database exists but contains no findings.")
        st.stop()

    filtered_findings = render_filters(all_findings)

    render_metric_cards(filtered_findings)

    st.divider()
    render_charts(filtered_findings)

    st.divider()
    render_findings_table(filtered_findings)

    st.divider()
    render_finding_details(filtered_findings)

    st.divider()
    render_comparison(all_findings)

    st.divider()
    st.caption(
        "Posture score is a portfolio-level heuristic and is not an official "
        "AWS Security Hub score."
    )


if __name__ == "__main__":
    main()
