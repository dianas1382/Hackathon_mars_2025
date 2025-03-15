import os
import dotenv
import boto3
import json
import base64
from flask import Flask, request, render_template


dotenv.load_dotenv(".env", override=True)


AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.environ.get('AWS_REGION')

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
    return render_template("recipe.html",recipe=getImageDescription(data))
@app.route('/')
def home():
    return render_template("index.html")




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
                        "text": "What are the ingredients of the image?"
                    }
                ]
            }
        ],
        "max_tokens": 10000,
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



if __name__ == '__main__':
    app.run(debug=True)


