from flask import Flask, request, render_template, jsonify
from notion_client import Client
import datetime
from huggingface_hub import InferenceClient

# -------- CONFIG --------

app = Flask(__name__)

HF_TOKEN = "yourownhuggingfacetoken"
client = InferenceClient(token=HF_TOKEN, model="HuggingFaceH4/zephyr-7b-beta")

NOTION_API_KEY = "yourownnotionkey"
NOTION_PROJECTS_DB_ID = "yourdatabaseid"

notion = Client(auth=NOTION_API_KEY)

chat_history = []


# -------- FUNCTIONS --------

def get_active_projects():
    projects = []
    next_cursor = None

    while True:
        response = notion.databases.query(
            database_id=NOTION_PROJECTS_DB_ID,
            filter={
                "property": "Status",
                "status": {"equals": "In Progress"}
            },
            start_cursor=next_cursor,
            page_size=100
        )

        for result in response["results"]:
            props = result["properties"]
            title = props["Project Name"]["title"][0]["text"]["content"]
            status = props["Status"]["status"]["name"]
            tags = ", ".join([t["name"] for t in props.get("Tags", {}).get("multi_select", [])])
            last_step = props.get("Last Step", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            next_step = props.get("Next Step", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            summary = props.get("Summary", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")

            projects.append(
                f"**{title}** – *{status}* – Tags: {tags}\n"
                f"  • **Last:** {last_step}\n"
                f"  • **Next:** {next_step}\n"
                f"  • **Summary:** {summary}"
            )

        if not response.get("has_more"):
            break
        next_cursor = response.get("next_cursor")

    return projects

def build_prompt(user_input: str):
    today = datetime.datetime.now().strftime("%A, %B %d, %Y")
    now = datetime.datetime.now().strftime("%I:%M %p")
    projects = get_active_projects()

    project_data = "\n\n".join([f"{i+1}. {p}" for i, p in enumerate(projects)])

    history_text = "\n".join([f"Nonchy: {u}\nAssistant: {a}" for u, a in chat_history])
    prompt = f"""
You are Nonchy's personal assistant and collaborator.

Today is {today}. It's currently {now}. Nonchy is a computer engineering student in Texas and also a recording artist/content creator in Morocco. He is working on multiple hardware and creative projects simultaneously, aiming to become both a world-class engineer and global artist.

Here is background context from Nonchy’s project tracker (stored in Notion). Use this to understand what he's actively working on — DO NOT repeat this back unless explicitly asked:

{project_data}

Use the chat history below to continue the conversation:

{history_text}

Nonchy: {user_input}
Assistant:
"""


    print("\n\n==== Prompt Sent to LLM ====\n")
    print(prompt)
    print("\n============================\n")
    return prompt.strip()

def get_openai_response(prompt):
    generation = client.text_generation(
        prompt=prompt,
        max_new_tokens=1024,
        temperature=0.7,
        top_p=0.95,
        repetition_penalty=1.1,
        stream=False
    )
    return generation

# -------- ROUTES --------

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/interact", methods=["POST"])
def interact():
    try:
        data = request.get_json(force=True)  # Works even if content-type is not set
        user_input = data.get("user_input", "").strip()
    except Exception as e:
        return jsonify({"response": "Error reading input."})

    if not user_input:
        return jsonify({"response": "Please enter something."})

    prompt = build_prompt(user_input)
    reply = get_openai_response(prompt)
    chat_history.append((user_input, reply))
    return jsonify({"response": reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
