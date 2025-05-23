
from flask import Flask, request, jsonify, render_template
import pandas as pd

# Initialize Flask app and secret key for session tracking
app = Flask(__name__)
app.secret_key = "your-secret-key"

# Load product data and fill blanks
df = pd.read_json("products_parsed.json")
df.fillna("", inplace=True)

# Normalize list-type fields so all values become lists
for col in ["Thickness", "OTR"]:
    df[col] = df[col].apply(lambda x: [x] if isinstance(x, str) else x if isinstance(x, list) else [])

# Filter flow and required columns
FILTER_ORDER = ["Application","Thickness", "Type", "WVTR", "OTR",  "Features"]
REQUIRED_COLS = ["Product Name"] + FILTER_ORDER

# In-memory user session store
user_sessions = {}

@app.route("/", methods=["GET"])
def index():
    # Optional: Send sorted filters if needed
    filters = {col: sorted(set(sum(df[col], [])) if isinstance(df[col].iloc[0], list) else df[col].dropna().unique())
               for col in FILTER_ORDER if col in df.columns}
    return render_template("index.html", filters=filters)

@app.route("/search", methods=["POST"])
def search():
    data = request.json
    query = data.get("query", "").strip()
    user_id = request.remote_addr
    session_data = user_sessions.get(user_id, {"answers": {}, "next_filter": FILTER_ORDER[0]})

    print("Session Data:", session_data)
    print("User Query:", query)

    # Main filter processing
    if session_data["next_filter"] in FILTER_ORDER:
        current_filter = session_data["next_filter"]
        session_data["answers"][current_filter] = query
        answered_filters = session_data["answers"]

        filtered = df.copy()
        for key, val in answered_filters.items():
            try:
                col_data = filtered.get(key)
                if col_data is not None:
                    if isinstance(col_data.iloc[0], list):
                        filtered = filtered[col_data.apply(lambda x: val.lower() in [str(i).lower().strip() for i in x])]
                    else:
                        filtered = filtered[col_data.fillna("").astype(str).str.lower().str.strip() == val.lower().strip()]
            except Exception as e:
                print(f"⚠️ Error filtering on {key}: {e}")

        # If no result, reset session and suggest
        if filtered.empty:
            failed_key = current_filter
            options = sorted(set(sum(df[failed_key], [])) if isinstance(df[failed_key].iloc[0], list)
                             else df[failed_key].dropna().unique().tolist())
            user_sessions.pop(user_id, None)
            return jsonify([{
                "Product Name": f"❌ Sorry, no match for {failed_key} = '{query}'. Try: " + ", ".join(options)
            }])

        # Determine next unanswered filter
        for f in FILTER_ORDER:
            if f not in answered_filters:
                if f in filtered.columns and not filtered[f].empty:
                    next_col = filtered[f]
                    options = sorted(set(sum(next_col, [])) if isinstance(next_col.iloc[0], list)
                                     else next_col.dropna().unique().tolist())
                    session_data["next_filter"] = f
                    user_sessions[user_id] = session_data
                    return jsonify([{
                        "Product Name": f"What {f} do you prefer? Options: " + ", ".join(options)
                    }])

        # Output top 3 results
        for col in REQUIRED_COLS:
            if col not in filtered.columns:
                filtered[col] = ""

        top_results = filtered[REQUIRED_COLS].head(3)
        user_sessions.pop(user_id, None)
        return jsonify(top_results.to_dict(orient="records"))

    # Start a new session
    session_data = {"answers": {}, "next_filter": FILTER_ORDER[0]}
    user_sessions[user_id] = session_data
    return jsonify([{
        "Product Name": "👋 Hello! Please tell me your desired Films with (e.g., Features, Types, WVTR)."
    }])

if __name__ == "__main__":
    app.run(debug=True)
