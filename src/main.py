import os
import uuid
import dotenv
import boto3
import json
import base64
import sqlite3
import jwt
from flask import Flask, flash, request, render_template, Response


dotenv.load_dotenv(".env", override=True)

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.environ.get('AWS_REGION')
JWT_SECRET = os.environ.get('JWT_SECRET')

bedrock_runtime_client = boto3.client(
    'bedrock-runtime',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)





model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"


app = Flask(__name__)

@app.route('/recipe', methods=["POST"])
def recipe():
    file = request.files["image"]
    data = file.stream.read()
    data = base64.b64encode(data).decode()
    desc = getImageDescription(data)
    result = json.loads(desc)
    return render_template("recipe.html",data=result)
@app.route('/')
def home():
    return render_template("index.html")

@app.route('/community',methods=['GET', 'POST'])
def community():
    conn = sqlite3.connect('user.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if request.method == 'POST' and 'content' in request.form:
        token = request.cookies.get("token")
        try:
            d = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except:
            return "unauthorized"
        creator = d['user']
        content = request.form['content']
        id = uuid.uuid4()
        uuidStr = str(id)
        cursor.execute('INSERT INTO post (creator, content, id) VALUES (?, ?, ?)', (creator, content, uuidStr))
        conn.commit()
        return "Post added successfully!"
        #flash('Post added successfully!', 'success')
    if request.method == 'POST' and 'comment_content' in request.form:
        token = request.cookies.get("token")
        try:
            d = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except:
            return "unauthorized"
        creator = d['user']
        post_id = request.form['post_id']
        content = request.form['comment_content']
        cursor.execute('INSERT INTO comment (id, creator, content) VALUES (?, ?, ?)', (post_id, creator, content))
        cursor.execute('SELECT * FROM comment WHERE id = ?', (post_id,))
        comments = cursor.fetchall()
        comments_str = 'OTHER COMMENT'.join([comment['content'] for comment in comments])
        cursor.execute('DELETE FROM aisummary WHERE id = ?', (post_id,))
        cursor.execute('INSERT INTO aisummary (id, content) VALUES (?, ?)', (post_id, getCommentSummary(comments_str)))
        conn.commit()
        return "Comment added successfully!"
        #flash('Comment added successfully!', 'success')
    cursor.execute('SELECT * FROM post')
    posts = cursor.fetchall()
    comments = {}
    summaries = {}
    for post in posts:
        cursor.execute('SELECT * FROM comment WHERE id = ?', (post['id'],))
        comments[post["id"]] = cursor.fetchall()
        cursor.execute('SELECT content FROM aisummary WHERE id = ?', (post['id'],))
        summaries[post["id"]] = cursor.fetchone()

    conn.close()

    return render_template("community.html",posts=posts,comments=comments,summaries=summaries)

@app.route('/my')
def my():
    token = request.cookies.get("token")
    try:
        d = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except:
        return "unauthorized"
    return d['user']

@app.route('/signin', methods=["GET","POST"])
def sign_in():
    if request.method == "GET":
        return render_template("signin.html")
    usercon = sqlite3.connect("user.db")
    usercur = usercon.cursor()
    user = request.form["user"]
    password = request.form["password"]
    if not user.isalnum() or not password.isalnum():
        return "Fields should only contain letters  and digits"
    res = usercur.execute(f"SELECT name, password FROM user WHERE name='{user}'AND password='{password}'").fetchone()
    if res is None:
        return "Not Found"
    resp = Response()
    token = jwt.encode({"user": user}, JWT_SECRET, algorithm="HS256")
    resp.headers["Set-Cookie"] = f"token={token}; HttpOnly; Secure; SameSite=Strict"
    return resp

@app.route('/signup', methods=["GET","POST"])
def sign_up():
    if request.method == "GET":
        return render_template("signup.html")
    usercon = sqlite3.connect("user.db")
    usercur = usercon.cursor()
    user = request.form["user"]
    password = request.form["password"]
    if not user.isalnum() or not password.isalnum():
        return "Fields should only contain letters and digits"
    res = usercur.execute(f"SELECT name, password FROM user WHERE name='{user}'").fetchone()
    if res is not None:
        return "User already exists"
    usercur.execute(f"""INSERT INTO user VALUES
        ('{user}', '{password}')""")
    usercon.commit()
    return "YAY"


def getImageDescription(encoded_image):
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": encoded_image
                        }
                    },
                    {
                        "type": "text",
                        "text": """What recipes can we make with the ingredients in the fridge? respond using ONLY json in culinary terms with excellent english in long and descriptive sentences. For instance : {
  'Omelette': [
    "Carefully break two or three eggs into a bowl, ensuring that no shells get in.",
    "Using a fork or whisk, beat the eggs until the yolks and whites are thoroughly combined.",
    Heat a non-stick skillet over medium heat and lightly coat it with a small amount of butter or oil.",
    "Pour the beaten eggs into the hot pan and let them cook for about 1-2 minutes until the edges begin to set.",
    "Once the edges are firm, gently lift one side of the omelette and fold it in half. Allow it to cook for an additional minute.",
    "Slide the omelette onto a plate and serve immediately. Optionally, add salt, pepper, or fillings such as cheese or vegetables."
  ],
  'Fruit Salad': [
    "Start by peeling the skin off one fresh apple using a vegetable peeler or knife.",
    "Cut the peeled apple into quarters, remove the core, and chop it into bite-sized cubes.",
    "For a well-rounded fruit salad, include fruits such as grapes, bananas, oranges, and strawberries. Peel and chop them accordingly.",
    "Combine all the chopped fruits in a large bowl. Stir gently to avoid bruising the delicate pieces.",
    "For extra flavor, drizzle a small amount of honey or a squeeze of lime juice over the fruit.",
    "Refrigerate the salad for 10-15 minutes before serving for a refreshing, cool treat."
  ]
}"""
                    }
                ]
            }
        ],
        "max_tokens": 100000,
        "anthropic_version": "bedrock-2023-05-31"
    }

    response = bedrock_runtime_client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        body=json.dumps(payload)
    )

    output_binary = response["body"].read()
    output_json = json.loads(output_binary)
    return output_json["content"][0]["text"]

def getCommentSummary(comments_str):
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Make a summary of the following comments : {comments_str}"
                    }
                ]
            }
        ],
        "max_tokens": 100000,
        "anthropic_version": "bedrock-2023-05-31"
    }

    response = bedrock_runtime_client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        body=json.dumps(payload)
    )

    output_binary = response["body"].read()
    output_json = json.loads(output_binary)
    return output_json["content"][0]["text"]

#with open('brk0s9daki0a1.jpg', 'rb') as image_file:
#    encoded_image = base64.b64encode(image_file.read()).decode()
#
#
#
#print(getImageDescription(encoded_image))



def get_db_connection():
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row  
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        )
    ''')
# Create comments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts (id)
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)