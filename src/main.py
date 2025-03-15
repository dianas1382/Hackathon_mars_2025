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
    desc = getImageDescription(data)
    result = json.loads(desc)
    return render_template("recipe.html",data=result)
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


#with open('brk0s9daki0a1.jpg', 'rb') as image_file:
#    encoded_image = base64.b64encode(image_file.read()).decode()
#
#
#
#print(getImageDescription(encoded_image))



if __name__ == '__main__':
    app.run(debug=True)


