from __future__ import annotations

import pandas as pd
import streamlit as st
from datetime import datetime


def analyze_data_for_chat(df: pd.DataFrame, question: str) -> str:
    """Token-free chat that analyzes data directly"""
    q_lower = question.lower()
    
    # Find relevant columns
    status_col = None
    assignee_col = None
    priority_col = None
    created_col = None
    due_col = None
    
    for col in df.columns:
        c_lower = col.lower()
        if c_lower == "status":
            status_col = col
        elif c_lower == "assignee":
            assignee_col = col
        elif "priority" in c_lower or "severity" in c_lower:
            priority_col = col
        elif "created" in c_lower:
            created_col = col
        elif "due" in c_lower:
            due_col = col
    
    total = len(df)
    
    # Answer patterns
    if any(word in q_lower for word in ["how many", "count", "total", "number of"]):
        if "in progress" in q_lower or "progress" in q_lower:
            if status_col:
                in_progress = df[status_col].astype(str).str.lower().isin(["in progress", "in-progress", "inprogress"]).sum()
                return f"There are **{in_progress}** tickets currently in progress."
        elif "completed" in q_lower or "done" in q_lower:
            if status_col:
                completed = df[status_col].astype(str).str.lower().isin(["done", "completed", "closed", "finished"]).sum()
                return f"There are **{completed}** completed tickets."
        elif "pending" in q_lower:
            if status_col:
                pending = df[status_col].astype(str).str.lower().isin(["pending", "backlog", "todo", "paused", "blocked"]).sum()
                return f"There are **{pending}** pending tickets."
        elif "active" in q_lower:
            if status_col:
                active = df[status_col].astype(str).str.lower().isin(["active", "ongoing"]).sum()
                return f"There are **{active}** active tickets."
        elif "blocked" in q_lower:
            if status_col:
                blocked = df[status_col].astype(str).str.lower().isin(["blocked"]).sum()
                return f"There are **{blocked}** blocked tickets."
        else:
            return f"There are **{total}** tickets in total."
    
    elif any(word in q_lower for word in ["who", "assignee", "assigned", "owner"]):
        if assignee_col:
            assignee_counts = df[assignee_col].value_counts().head(5)
            if len(assignee_counts) > 0:
                result = "Top assignees:\n"
                for name, count in assignee_counts.items():
                    result += f"- **{name}**: {count} tickets\n"
                return result
            return "No assignee information available."
        return "Assignee column not found in the data."
    
    elif any(word in q_lower for word in ["status", "statuses", "states"]):
        if status_col:
            status_counts = df[status_col].value_counts()
            result = "Status distribution:\n"
            for status, count in status_counts.items():
                pct = (count / total * 100) if total > 0 else 0
                result += f"- **{status}**: {count} ({pct:.1f}%)\n"
            return result
        return "Status column not found."
    
    elif any(word in q_lower for word in ["priority", "priorities", "severity"]):
        if priority_col:
            priority_counts = df[priority_col].value_counts()
            result = "Priority breakdown:\n"
            for priority, count in priority_counts.items():
                result += f"- **{priority}**: {count} tickets\n"
            return result
        return "Priority column not found in the data."
    
    elif any(word in q_lower for word in ["overdue", "late", "past due"]):
        if due_col and created_col:
            now = datetime.now()
            df_copy = df.copy()
            df_copy["due_dt"] = pd.to_datetime(df_copy[due_col], errors="coerce")
            overdue = df_copy[df_copy["due_dt"] < pd.Timestamp(now)].copy()
            if len(overdue) > 0:
                return f"There are **{len(overdue)}** overdue tickets (past their due date)."
            return "No overdue tickets found."
        return "Due date column not found."
    
    elif any(word in q_lower for word in ["summary", "overview", "insights"]):
        if status_col:
            status_counts = df[status_col].value_counts()
            in_progress = df[status_col].astype(str).str.lower().isin(["in progress", "in-progress", "inprogress"]).sum()
            completed = df[status_col].astype(str).str.lower().isin(["done", "completed", "closed", "finished"]).sum()
            pending = df[status_col].astype(str).str.lower().isin(["pending", "backlog", "todo", "paused", "blocked"]).sum()
            
            result = f"**Dashboard Summary:**\n\n"
            result += f"Total tickets: **{total}**\n"
            result += f"- In Progress: **{in_progress}** ({in_progress/total*100:.1f}%)\n" if total > 0 else ""
            result += f"- Completed: **{completed}** ({completed/total*100:.1f}%)\n" if total > 0 else ""
            result += f"- Pending: **{pending}** ({pending/total*100:.1f}%)\n" if total > 0 else ""
            
            if assignee_col:
                top_assignee = df[assignee_col].value_counts().head(1)
                if len(top_assignee) > 0:
                    result += f"\nTop assignee: **{top_assignee.index[0]}** with {top_assignee.iloc[0]} tickets"
            
            return result
        return "Unable to generate summary - status column not found."
    
    elif any(word in q_lower for word in ["help", "what can", "questions"]):
        return """**I can answer questions about:**
- How many tickets (total, in progress, completed, pending, blocked)
- Status distribution
- Assignee information
- Priority breakdown
- Overdue tickets
- Summary and insights

Try asking: "How many tickets are in progress?" or "Who has the most tickets?" or "Show me a summary"
"""
    
    # Default response
    return f"I can help you analyze the **{total}** tickets in the dashboard. Try asking about:\n- Ticket counts by status\n- Assignee workload\n- Priority distribution\n- Overdue tickets\n- Overall summary\n\nOr type 'help' for more options."


def local_chat_ui(filtered_df: pd.DataFrame) -> None:
    """Token-free chat interface"""
    st.subheader("💬 Data Assistant")
    
    if "local_chat_history" not in st.session_state:
        st.session_state.local_chat_history = []  # type: ignore[attr-defined]
    
    # Show chat history
    for msg in st.session_state.local_chat_history:  # type: ignore[attr-defined]
        st.chat_message(msg["role"]).write(msg["content"])  # type: ignore[index]
    
    # Chat input
    user_msg = st.chat_input("Ask about your tickets (e.g., 'How many are in progress?')")
    
    if user_msg:
        # Add user message
        st.session_state.local_chat_history.append({"role": "user", "content": user_msg})  # type: ignore[attr-defined]
        st.chat_message("user").write(user_msg)
        
        # Generate response
        with st.chat_message("assistant"):
            answer = analyze_data_for_chat(filtered_df, user_msg)
            st.markdown(answer)
            st.session_state.local_chat_history.append({"role": "assistant", "content": answer})  # type: ignore[attr-defined]
        
        st.rerun()
    
    # Clear button
    if st.button("🗑️ Clear Chat", key="clear_local_chat"):
        st.session_state.local_chat_history = []  # type: ignore[attr-defined]
        st.rerun()

