import httpx
import pandas as pd
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="RailSense-AI", layout="wide")

page = st.sidebar.selectbox("Navigation", ["Live Overview", "Sensor Explorer", "Alert Feed", "Model Comparison"])


def fetch(endpoint: str, params: dict | None = None) -> list[dict]:
    try:
        r = httpx.get(f"{API_BASE}{endpoint}", params=params, timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return []


if page == "Live Overview":
    st.title("RailSense-AI — Live Overview")

    col1, col2, col3, col4 = st.columns(4)
    anomalies = fetch("/api/anomalies", {"limit": 500})

    with col1:
        critical = [a for a in anomalies if a["severity"] == "critical"]
        st.metric("Critical Alerts", len(critical))
    with col2:
        warning = [a for a in anomalies if a["severity"] == "warning"]
        st.metric("Warnings", len(warning))
    with col3:
        trains = set(a["train_id"] for a in anomalies)
        st.metric("Affected Trains", len(trains))
    with col4:
        total = len(anomalies)
        health = max(0, 100 - total)
        st.metric("System Health", f"{health}%")

    if anomalies:
        st.subheader("Recent Anomalies by Line")
        df = pd.DataFrame(anomalies)
        st.dataframe(df[["timestamp", "train_id", "line_id", "sensor_type", "severity", "anomaly_score"]], use_container_width=True)


elif page == "Sensor Explorer":
    st.title("Sensor Explorer")

    train_id = st.selectbox("Train Unit", ["T001", "T002", "T003", "T004", "T005"])
    sensor_type = st.selectbox("Sensor", ["vibration", "temperature", "door_cycle", "current_draw"])

    readings = fetch("/api/sensors", {"train_id": train_id, "sensor_type": sensor_type, "limit": 1000})

    if readings:
        df = pd.DataFrame(readings)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        # Plot sensor values
        st.subheader(f"{sensor_type} — {train_id}")
        st.line_chart(df.set_index("timestamp")["value"])

        # Overlay anomalies if any
        anomalies = fetch("/api/anomalies", {"train_id": train_id, "limit": 200})
        if anomalies:
            anom_df = pd.DataFrame(anomalies)
            anom_df = anom_df[anom_df["sensor_type"] == sensor_type]
            if not anom_df.empty:
                st.subheader("Detected Anomalies")
                st.dataframe(anom_df[["timestamp", "anomaly_score", "severity", "detection_method"]], use_container_width=True)
    else:
        st.warning("No sensor data found. Run the seed script first.")


elif page == "Alert Feed":
    st.title("Alert Feed")

    severity_filter = st.multiselect("Filter by severity", ["critical", "warning"], default=["critical", "warning"])
    anomalies = fetch("/api/anomalies", {"limit": 200})

    if anomalies:
        df = pd.DataFrame(anomalies)
        df = df[df["severity"].isin(severity_filter)]

        for _, row in df.iterrows():
            severity_color = "\U0001f534" if row["severity"] == "critical" else "\U0001f7e1"
            with st.expander(f"{severity_color} {row['train_id']} — {row['sensor_type']} ({row['severity']}) — {row['timestamp']}"):
                st.write(f"**Score:** {row['anomaly_score']:.2f}")
                st.write(f"**Line:** {row['line_id']} | **Station:** {row['station_id']}")
                st.write(f"**Detection Method:** {row['detection_method']}")

                if st.button("Request AI Analysis", key=f"assess_{row['id']}"):
                    with st.spinner("Analyzing..."):
                        r = httpx.post(f"{API_BASE}/api/assess/{row['id']}", timeout=30.0)
                        if r.status_code == 200:
                            assessment = r.json()
                            st.success(f"**Root Cause:** {assessment['root_cause']}")
                            st.info(f"**Action:** {assessment['recommended_action']}")
                            st.caption(f"**Reasoning:** {assessment['reasoning']}")
                        else:
                            st.error("Analysis failed")
    else:
        st.info("No anomalies detected yet.")


elif page == "Model Comparison":
    st.title("Model Comparison — STL vs Prophet")

    st.write("Comparing detection performance on synthetic data with known anomalies.")

    if st.button("Run Comparison"):
        with st.spinner("Running STL and Prophet detectors... (Prophet may take a minute)"):
            from src.ingestion.synthetic_gen import SyntheticGenerator, AnomalyScenario
            from src.detection.compare import compare_detectors

            gen = SyntheticGenerator(seed=99)
            scenario = AnomalyScenario(sensor_types=["temperature"], start_hour=12, duration_hours=2, magnitude=4.0)
            df = gen.generate(train_id="COMPARE", hours=48, anomalies=[scenario])
            temp_df = df[df["sensor_type"] == "temperature"].reset_index(drop=True)

            metrics = compare_detectors(temp_df)

            col1, col2 = st.columns(2)
            for col, (name, m) in zip([col1, col2], metrics.items()):
                with col:
                    st.subheader(name.upper())
                    st.metric("Precision", f"{m['precision']:.2%}")
                    st.metric("Recall", f"{m['recall']:.2%}")
                    st.metric("F1 Score", f"{m['f1']:.2%}")
                    st.metric("Computation Time", f"{m['time_seconds']}s")
                    st.metric("Total Flagged", m["total_flagged"])

            st.subheader("Sensor Data with Anomaly Window")
            st.line_chart(temp_df.set_index("timestamp")["value"])
