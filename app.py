import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from snowflake.snowpark.context import get_active_session

st.set_page_config(layout="wide", page_title="AI for Good: Data Clean Room")
st.title("🛡️ AI for Good: Shared Analysis Zone")
st.write("Securely analyzing Bank + Insurance trends via Snowflake Cortex AI.")

session = get_active_session()

if 'history' not in st.session_state:
    st.session_state.history = []
if 'query_text' not in st.session_state:
    st.session_state.query_text = ""

try:
    session.use_warehouse("COMPUTE_WH")
    df = session.table("SHARED_ZONE.PUBLIC.CROSS_ORG_INSIGHTS").to_pandas()
except Exception as e:
    st.error(f"❌ Connection/Data Error: {e}")
    st.stop()

with st.sidebar:
    st.header("🛡️ Privacy Controls")
    st.success("Data Clean Room: **Active**")
    
    
    st.divider()
    st.header("👤 View Persona")
    persona = st.radio("Tailor Insights For:", 
                      ["Policy Maker", "Bank Executive", "Insurance Underwriter"],
                      help="Changes the AI's perspective and tone.")
    
    st.divider()
    st.header("🎯 Goal Simulator")
    reduction_target = st.slider("Target Claim Reduction (%)", 0, 50, 15)
    
    if not df.empty:
        total_current_claims = df['TOTAL_INSURANCE_CLAIMS'].sum()
        projected_savings = total_current_claims * (reduction_target / 100)
        st.metric("Projected Savings", f"${projected_savings:,.0f}")
    
    st.divider()
    if st.button("Clear Cache & Reset"):
        st.session_state.history = []
        st.rerun()

st.subheader("📌 Shared Zone Highlights")
if not df.empty:
    m_col1, m_col2, m_col3 = st.columns([1, 1, 1.5])
    
    with m_col1:
        st.metric("Total Liability", f"${df['TOTAL_INSURANCE_CLAIMS'].sum():,.0f}")
        st.metric("Avg. Credit Score", f"{df['AVG_CREDIT_SCORE'].mean():.0f}")
    
    with m_col2:
        st.metric("Lives Impacted", f"{df['HOUSEHOLD_COUNT'].sum()}")
        top_risk = df.loc[df['TOTAL_INSURANCE_CLAIMS'].idxmax()]['AGE_GROUP']
        st.warning(f"High Risk: {top_risk}")

    with m_col3:
        raw_risk = (df['TOTAL_INSURANCE_CLAIMS'].mean() / df['AVG_CREDIT_SCORE'].mean()) * 5
        risk_index = min(max(raw_risk, 0), 100) # Keep between 0-100
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = risk_index,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Community Risk Index", 'font': {'size': 18}},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkred"},
                'steps': [
                    {'range': [0, 40], 'color': "#1B8720"}, 
                    {'range': [40, 70], 'color': "#FF9400"}, 
                    {'range': [70, 100], 'color': "#FF1708"}] 
            }))
        fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

else:
    st.info("Waiting for data...")

st.divider()
st.subheader("🤖 Ask the AI Analyst")

def set_query(text):
    st.session_state.query_text = text

st.write("🔍 **Quick Analysis Shortcuts:**")
q_col1, q_col2, q_col3 = st.columns(3)
with q_col1:
    if st.button("Analyze Young Adult Risk"): set_query("Analyze the 18-25 age group's claims vs credit health.")
with q_col2:
    if st.button("High Liability Segments"): set_query("Which segment has the highest total insurance liability?")
with q_col3:
    if st.button("Financial Health Trends"): set_query("Show me the relationship between credit scores and risk levels.")

user_input = st.text_input("Enter your question here:", value=st.session_state.query_text)

if user_input:
    with st.spinner(f"AI ({persona} Mode) is analyzing..."):
        try:
            yaml_content = session.sql("SELECT $1 FROM @SHARED_ZONE.PUBLIC.MODELS_STAGE/social_impact_model.yaml").collect()[0][0]
            
            master_prompt = (f"Act as a {persona}. Use this YAML context: {yaml_content}. "
                           f"Question: {user_input}. Base your answer ONLY on SHARED_ZONE.PUBLIC.CROSS_ORG_INSIGHTS.")
            
            safe_prompt = master_prompt.replace("'", "''")
            response = session.sql(f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-7b', '{safe_prompt}')").collect()[0][0]
            
            st.session_state.history.append({"q": user_input, "p": persona, "a": response})
            
            st.info(f"💡 AI Insight (for {persona}):")
            st.write(response)

            st.subheader("📊 Visual Trend Analysis")
            v1, v2 = st.columns(2)
            with v1:
                st.plotly_chart(px.scatter(df, x="AGE_GROUP", y="TOTAL_INSURANCE_CLAIMS", 
                                          size="AVG_CREDIT_SCORE", color="AGE_GROUP", 
                                          title="Claims vs Credit Health"), use_container_width=True)
            with v2:
                st.plotly_chart(px.bar(df, x="AGE_GROUP", y="TOTAL_INSURANCE_CLAIMS", 
                                      color="AGE_GROUP", title="Liability by Age Group"), use_container_width=True)
        except Exception as e:
            st.error(f"Analysis failed: {e}")

st.divider()
h_col1, h_col2 = st.columns([2, 1])

with h_col1:
    if st.session_state.history:
        with st.expander("🕒 Recent AI Conversations"):
            for chat in reversed(st.session_state.history[-3:]):
                st.write(f"**Persona:** {chat['p']} | **Q:** {chat['q']}")
                st.write(f"**A:** {chat['a']}")
                st.divider()

with h_col2:
    if not df.empty:
        st.write("📤 **Export Zone**")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Download Insights (CSV)", data=csv, 
                           file_name='clean_room_data.csv', mime='text/csv')