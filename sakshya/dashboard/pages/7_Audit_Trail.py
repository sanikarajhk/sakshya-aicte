"""
Sakshya Dashboard - Cryptographic Audit Trail
Inspects immutable hash-chained event logs and verifies SHA-256 chain continuity.
"""

import sys
from pathlib import Path

# Automatically add repository root to sys.path for Streamlit Cloud
CURRENT_DIR = Path(__file__).resolve()
for parent in [CURRENT_DIR] + list(CURRENT_DIR.parents):
    if (parent / "sakshya").is_dir() and (parent / "sakshya" / "core").is_dir():
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))
        break

import streamlit as st
import pandas as pd
import json
from sakshya.core.database import get_db_context
from sakshya.core.models import AuditLogDB
from sakshya.core.audit import verify_audit_chain
from sakshya.dashboard.responsive import inject_responsive_css

st.set_page_config(page_title="Audit Trail | Sakshya", page_icon="⚖️", layout="wide")
inject_responsive_css()

# Government Masthead Banner
st.markdown("""
<div class="gov-masthead">
    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #FEF3C7; font-weight: 700; margin-bottom: 4px;">
        All India Council for Technical Education • Regulatory Governance & Compliance
    </div>
    <h1 class="gov-masthead-title">Cryptographic Hash-Chained Audit Trail</h1>
    <p class="gov-masthead-subtitle">
        Tamper-evident regulatory ledger ensuring non-repudiation and chronological integrity of all dossier uploads, system findings, and officer adjudications
    </p>
</div>
""", unsafe_allow_html=True)

# Verification Section
with get_db_context() as db:
    audit_result = verify_audit_chain(db)
    all_logs = [
        {
            "id": l.id,
            "timestamp": l.timestamp,
            "actor_id": l.actor_id,
            "actor_role": l.actor_role,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "current_hash": l.current_hash,
            "prev_hash": l.prev_hash,
            "details_json": l.details_json
        }
        for l in db.query(AuditLogDB).order_by(AuditLogDB.id.desc()).all()
    ]

col_v1, col_v2 = st.columns([1, 2])
with col_v1:
    if audit_result.get("valid"):
        st.markdown(f"""
        <div class="gov-card" style="border-left: 5px solid #166534; padding: 12px 16px;">
            <span class="gov-badge gov-badge-verified">Chain Continuity Verified</span>
            <h3 style="margin: 4px 0 2px 0; color: #166534;">Audit Ledger Integrity Intact</h3>
            <div style="font-size: 12.5px; color: #334155; margin-top: 4px;">
                Verified cryptographic blocks: <b>{audit_result.get('total_records', 0)}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="gov-card" style="border-left: 5px solid #B91C1C; padding: 12px 16px;">
            <span class="gov-badge gov-badge-flagged">Integrity Breach</span>
            <h3 style="margin: 4px 0 2px 0; color: #991B1B;">Tampering Detected in Ledger</h3>
            <div style="font-size: 12.5px; color: #7F1D1D; margin-top: 4px;">{audit_result.get('error')}</div>
        </div>
        """, unsafe_allow_html=True)

with col_v2:
    st.markdown("""
    <div class="gov-card" style="padding: 12px 16px;">
        <div style="font-size: 11px; text-transform: uppercase; color: #64748B; font-weight: 700; margin-bottom: 2px;">Ledger Security Architecture</div>
        <div style="font-size: 12.5px; color: #334155; line-height: 1.45;">
            Each audit entry is chained to its predecessor via SHA-256:<br>
            <code>H(n) = SHA256( H(n-1) || Timestamp || Actor || Action || Entity || Canonical_JSON(Details) )</code><br>
            Any retrospective alteration of records instantly invalidates downstream cryptographic hash pointers.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if audit_result.get("valid"):
        st.caption(f"Latest Block Hash Pointer: `{audit_result.get('latest_block_hash')}`")

st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px solid #CBD5E1;'>", unsafe_allow_html=True)

# Filter Audit Logs
st.subheader(f"Audit Block Ledger ({len(all_logs)} Blocks)")

action_types = sorted(list(set(l["action"] for l in all_logs)))
selected_action = st.selectbox("Filter by Action Type", ["ALL"] + action_types)

filtered_logs = all_logs if selected_action == "ALL" else [l for l in all_logs if l["action"] == selected_action]

log_rows = []
for l in filtered_logs:
    log_rows.append({
        "Block ID": l["id"],
        "Timestamp (UTC)": l["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
        "Actor (Role)": f"{l['actor_id']} ({l['actor_role']})",
        "Action Event": l["action"],
        "Entity Reference": f"{l['entity_type']}:{l['entity_id']}",
        "Block SHA-256 Hash": l["current_hash"][:20] + "...",
        "Prev Hash Pointer": l["prev_hash"][:16] + "..."
    })

df_logs = pd.DataFrame(log_rows)
st.dataframe(df_logs, use_container_width=True)

# Detailed Block Inspector
st.subheader("🔎 Individual Block Forensic Inspector")
if all_logs:
    selected_block_id = st.selectbox("Select Block ID to inspect payload", [l["id"] for l in all_logs])
    chosen_block = next(l for l in all_logs if l["id"] == selected_block_id)

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.markdown("**Block Header:**")
        st.json({
            "block_id": chosen_block["id"],
            "timestamp": chosen_block["timestamp"].isoformat(),
            "actor_id": chosen_block["actor_id"],
            "actor_role": chosen_block["actor_role"],
            "action": chosen_block["action"],
            "entity": f"{chosen_block['entity_type']}:{chosen_block['entity_id']}",
            "previous_hash": chosen_block["prev_hash"],
            "current_hash": chosen_block["current_hash"]
        })
    with col_b2:
        st.markdown("**Payload Content (Canonical Details):**")
        st.json(json.loads(chosen_block["details_json"]))
