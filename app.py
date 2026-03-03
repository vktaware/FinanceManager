import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# Configuration
st.set_page_config(page_title="10-Year Financial Intelligence", layout="wide")

@st.cache_data
def load_data():
    try:
        df = pd.read_excel("NEW_Consolodated10YearsStatementsICICI_1454_2016To25.xlsx")
        
        # User manually provided YEAR, let's remap it to Year for exact compatibility with our sidebar
        if 'YEAR' in df.columns and 'Year' not in df.columns:
            df.rename(columns={'YEAR': 'Year'}, inplace=True)
            
        # Ensure proper Date formatting from their file (they might be DD/MM/YYYY inside the sheet)
        # Use dayfirst to parse 07/03/2016 accurately
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        
        # Ensure Month / Year_Month are present if they got lost in manual edit
        if 'Month' not in df.columns:
            df['Month'] = df['Date'].dt.month
        if 'Year_Month' not in df.columns:
            df['Year_Month'] = df['Date'].dt.to_period('M').astype(str)
            
        return df
    except Exception as e:
        st.error(f"Error loading new consolidated data: {e}")
        return pd.DataFrame()

def load_mapping():
    try:
        with open("category_mapping.json", "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading category mapping: {e}")
        return {}

def categorize_transaction(particulars, mapping):
    particulars_upper = particulars.upper()
    for category, keywords in mapping.items():
        for keyword in keywords:
            if keyword.upper() in particulars_upper:
                return category
    return "Other / Uncategorized"

# Load data and map
df = load_data()
mapping = load_mapping()

if df.empty:
    st.error("Data not loaded. Please ensure extraction script ran successfully.")
    st.stop()

if 'Category' not in df.columns:
    df['Category'] = df['Particulars'].apply(lambda x: categorize_transaction(x, mapping))


# Build comprehensive category list
existing_cats = list(df['Category'].dropna().unique()) if 'Category' in df.columns else []
mapped_cats = list(mapping.keys())
categories = sorted(list(set(existing_cats + mapped_cats + ["Other / Uncategorized"])))

# --- Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Reporting", "AI Analyst", "Settings"])
st.sidebar.divider()

# --- Common Sidebar Controls ---
st.sidebar.title("🛠️ Global Filters")
st.sidebar.success(f"Database Loaded: {len(df):,} records")

# 1. Date Range Selection
min_date = df['Date'].min().date()
max_date = df['Date'].min().replace(year=df['Date'].min().year + 9).date()
date_range = st.sidebar.date_input("Select Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

# 2. Category Filter
selected_categories = st.sidebar.multiselect("Filter by Category", categories, default=categories)

# Apply Global Filters
if len(date_range) == 2:
    start_date, end_date = date_range
    mask = (df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)
else:
    mask = [True] * len(df) # Fallback if incomplete date selection

mask = mask & (df['Category'].isin(selected_categories))
filtered_df = df[mask]

def format_inr(value):
    return f"₹{value:,.0f}"

# --- Page Logic ---
if page == "Dashboard":
    st.title("📊 Financial Dashboard")
    st.markdown("---")

    total_inflow = filtered_df['Deposits'].sum()
    total_outflow = filtered_df['Withdrawals'].sum()
    net_cashflow = total_inflow - total_outflow

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Inflow (Income)", format_inr(total_inflow))
    c2.metric("Total Outflow (Expenses)", format_inr(total_outflow))
    c3.metric("Net Cashflow", format_inr(net_cashflow), delta=f"{format_inr(net_cashflow)}", delta_color="normal")
    c4.metric("Transactions Found", f"{len(filtered_df):,}")

    st.subheader("Account Balance Trend")
    trend_df = filtered_df.sort_values('Date')
    daily_bal = trend_df.drop_duplicates(subset='Date', keep='last')
    fig1 = px.line(daily_bal, x='Date', y='Balance', markers=False)
    fig1.update_traces(line_color='blue')
    st.plotly_chart(fig1, use_container_width=True)

elif page == "Reporting":
    st.title("📑 Reporting Engine")
    st.markdown("---")
    
    # Report-specific filters
    col1, col2 = st.columns(2)
    with col1:
        report_type = st.selectbox("Select Report Type", ["Cashflow Summary", "Expense Breakdown", "Transaction Explorer", "Anomaly Detection"])
    with col2:
        particulars_search = st.text_input("Search Particulars (e.g. Amazon, UPI)", "")

    # Apply particulars search for reports
    if particulars_search:
        report_df = filtered_df[filtered_df['Particulars'].str.contains(particulars_search, case=False, na=False)]
    else:
        report_df = filtered_df

    if report_type == "Cashflow Summary":
        st.subheader("Monthly Cashflow Summary")
        monthly_summary = report_df.groupby('Year_Month')[['Deposits', 'Withdrawals']].sum().reset_index()
        fig_cf = go.Figure()
        fig_cf.add_trace(go.Bar(x=monthly_summary['Year_Month'], y=monthly_summary['Deposits'], name='Inflow', marker_color='green'))
        fig_cf.add_trace(go.Bar(x=monthly_summary['Year_Month'], y=monthly_summary['Withdrawals'], name='Outflow', marker_color='red'))
        fig_cf.update_layout(barmode='group', xaxis_title="Month", yaxis_title="Amount (₹)")
        st.plotly_chart(fig_cf, use_container_width=True)
        
        st.dataframe(monthly_summary.sort_values('Year_Month', ascending=False), use_container_width=True, hide_index=True)

    elif report_type == "Expense Breakdown":
        st.subheader("Expense Distribution by Category")
        spend_df = report_df[report_df['Withdrawals'] > 0]
        if not spend_df.empty:
            cat_spend = spend_df.groupby('Category')['Withdrawals'].sum().reset_index()
            fig_pie = px.pie(cat_spend, values='Withdrawals', names='Category', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            st.dataframe(cat_spend.sort_values('Withdrawals', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No outflow data in selected range.")

    elif report_type == "Transaction Explorer":
        st.subheader("Transaction Explorer & Categorization")
        st.metric("Total Matches", f"{len(report_df):,}")
        
        st.markdown("### Mass Categorization")
        st.write("1. Check the boxes next to the transactions (or use Select All).")
        st.write("2. Pick a category and click **Apply to Selected**.")
        
        if 'select_all' not in st.session_state:
            st.session_state.select_all = False
        if 'editor_key' not in st.session_state:
            st.session_state.editor_key = 0

        col_sa, col_da, col_cat, col_app = st.columns([1, 1, 2, 2])
        
        with col_sa:
            if st.button("Select All", use_container_width=True):
                st.session_state.select_all = True
                st.session_state.editor_key += 1
                st.rerun()
        with col_da:
            if st.button("Deselect All", use_container_width=True):
                st.session_state.select_all = False
                st.session_state.editor_key += 1
                st.rerun()
                
        with col_cat:
            mass_category = st.selectbox("Assign Category", categories, key="mass_cat", label_visibility="collapsed")
            
        sorted_report_df = report_df.sort_values('Date', ascending=False).copy()
        sorted_report_df.insert(0, "Select", st.session_state.select_all)
        
        edited_df = st.data_editor(
            sorted_report_df[['Select', 'Date', 'Particulars', 'Category', 'Deposits', 'Withdrawals', 'Balance']], 
            use_container_width=True,
            hide_index=False,
            key=f"tx_editor_{st.session_state.editor_key}",
            column_config={
                "Select": st.column_config.CheckboxColumn("Select", default=st.session_state.select_all),
                "Date": st.column_config.Column(disabled=True),
                "Particulars": st.column_config.Column(disabled=True),
                "Deposits": st.column_config.Column(disabled=True),
                "Withdrawals": st.column_config.Column(disabled=True),
                "Balance": st.column_config.Column(disabled=True),
                "Category": st.column_config.SelectboxColumn(
                    "Category",
                    help="Select the category",
                    width="medium",
                    options=categories,
                    required=True,
                )
            }
        )
        
        with col_app:
            if st.button("Apply to Selected", type="primary", use_container_width=True):
                selected_rows = edited_df[edited_df['Select'] == True]
                if not selected_rows.empty:
                    df.loc[selected_rows.index, 'Category'] = mass_category
                    df.to_excel("NEW_Consolodated10YearsStatementsICICI_1454_2016To25.xlsx", index=False)
                    st.session_state.select_all = False
                    st.session_state.editor_key += 1
                    load_data.clear()
                    st.rerun()
                else:
                    st.warning("No rows selected.")
        
        # Check what changed individually
        changes = edited_df['Category'] != sorted_report_df['Category']
        if changes.any():
            st.warning(f"You have unsaved manual changes in {changes.sum()} row(s).")
            if st.button("Save Individual Changes"):
                df.loc[edited_df.index, 'Category'] = edited_df['Category']
                df.to_excel("NEW_Consolodated10YearsStatementsICICI_1454_2016To25.xlsx", index=False)
                st.session_state.editor_key += 1
                st.success("Changes saved!")
                load_data.clear()
                st.rerun()

    elif report_type == "Anomaly Detection":
        st.subheader("Potential Duplicates (Same Day, Same Amount)")
        dup_mask = report_df.duplicated(subset=['Date', 'Withdrawals'], keep=False)
        duplicates = report_df[dup_mask & (report_df['Withdrawals'] > 0)].sort_values(by=['Date', 'Withdrawals'])
        st.dataframe(duplicates[['Date', 'Particulars', 'Category', 'Withdrawals']], use_container_width=True, hide_index=True)

elif page == "AI Analyst":
    st.title("🤖 AI Financial Analyst")
    st.markdown("---")
    
    st.markdown("### LLM Configuration")
    api_key = st.text_input("Enter your Gemini API Key", type="password", help="Get your free key from Google AI Studio")
    
    if not api_key:
        st.warning("Please enter your Gemini API Key to start the analysis.")
        st.stop()
        
    st.info("The AI receives context based on your current **Global Filters** (Date selected and Categories).")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
        
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    user_query = st.chat_input("Ask about your finances... (e.g., 'What are my top 3 recurring expenses?')")
    
    if user_query:
        # Show user message
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)
            
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your finances..."):
                try:
                    from google import genai
                    client = genai.Client(api_key=api_key)
                    
                    # Prepare Context
                    total_inflow = filtered_df['Deposits'].sum()
                    total_outflow = filtered_df['Withdrawals'].sum()
                    
                    context_str = f"""
                    You are an expert personal financial advisor analyzing the user's bank statements.
                    The user has currently filtered their data to the following constraints:
                    - Date Range: {date_range}
                    - Filtered Transactions Count: {len(filtered_df)}
                    - Total Inflow: ₹{total_inflow:,.0f}
                    - Total Outflow: ₹{total_outflow:,.0f}
                    
                    Here are recent/relevant transactions (up to 100 rows):
                    {filtered_df[['Date', 'Particulars', 'Category', 'Deposits', 'Withdrawals', 'Balance']].head(100).to_markdown()}
                    """
                    
                    # Construct conversation history for the LLM
                    # Google GenAI SDK can handle full chat history if we use Chats, but for simplicity, we pass recent context directly.
                    # Or we just pass the system instructions + the newest prompt. Let's do a direct generation.
                    
                    prompt = f"{context_str}\n\nUser Question: {user_query}"
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                    )
                    
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                    
                except Exception as e:
                    st.error(f"Error calling Gemini: {e}")

elif page == "Settings":
    st.title("⚙️ Settings")
    st.markdown("---")
    
    st.subheader("Category Management")
    st.write("Add new categories (and optional keywords comma-separated) to be used across the app.")
    
    with st.container(border=True):
        st.markdown("#### Add New Category")
        with st.form("add_category_form", clear_on_submit=True):
            new_cat_name = st.text_input("New Category Name *").strip()
            new_cat_keywords = st.text_input("Keywords (comma separated, optional)", help="E.g. Swiggy, Zomato, Food")
            submit_cat = st.form_submit_button("Save Category", type="primary")
            
            if submit_cat:
                if not new_cat_name:
                    st.error("Category Name is required.")
                else:
                    existing_lower = [c.lower() for c in categories]
                    if new_cat_name.lower() in existing_lower:
                        st.error(f"Category '{new_cat_name}' already exists!")
                    else:
                        keywords_list = [k.strip() for k in new_cat_keywords.split(",")] if new_cat_keywords.strip() else []
                        # Add to mapping
                        mapping[new_cat_name] = keywords_list
                        try:
                            with open("category_mapping.json", "w") as f:
                                json.dump(mapping, f, indent=4)
                            # Data refresh might be needed here to re-evaluate the mapping?
                            # Not strictly necessary if they just want the category to show up in lists,
                            # but it's good practice. We'll just show success and rerun.
                            load_data.clear() # clear data cache if category logic changed
                            st.success(f"Category '{new_cat_name}' added successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to save to config file: {e}")

    st.markdown("### Existing Configured Categories")
    # Display the current mapping
    if mapping:
        map_df = pd.DataFrame([{"Category": k, "Keywords": ", ".join(v)} for k, v in mapping.items()])
        st.dataframe(map_df, use_container_width=True, hide_index=True)
    else:
        st.info("No categories defined in config file yet.")

