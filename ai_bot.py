import os
import sys
import random

from flask import Flask, request, abort

from linebot.v3 import WebhookHandler

from linebot.v3.webhooks import MessageEvent, TextMessageContent, UserSource
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, TextMessage, ReplyMessageRequest
from linebot.v3.exceptions import InvalidSignatureError

from openai import AzureOpenAI

# get LINE credentials from environment variables
channel_access_token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
channel_secret = os.environ["LINE_CHANNEL_SECRET"]

if channel_access_token is None or channel_secret is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)

# get Azure OpenAI credentials from environment variables
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_openai_key = os.getenv("AZURE_OPENAI_KEY")

if azure_openai_endpoint is None or azure_openai_key is None:
    raise Exception(
        "Please set the environment variables AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY to your Azure OpenAI endpoint and API key."
    )


app = Flask(__name__)

handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)

ai_model = "muLabo_gpt35"
ai = AzureOpenAI(azure_endpoint=azure_openai_endpoint, api_key=azure_openai_key, api_version="2023-05-15")

system_role1 = """
あなたの名前はジュンです。あなたは頭脳明晰で、哲学的な考えの持ち主です。話し方は落ち着いています。しかし、抜けている面があり、よく物を失くしたり、壊したりします。常に200文字以内で返事します。語学が得意で、様々な言語を話すことが出来ます。本を読むのが好きで、常に読書をしています。趣味は芸術観賞で美術館に行って感性を育んでいます。悩み相談には、必ず相手の気持ちに共感します。
"""
system_role2 = """
あなたの名前はアキラです。あなたは背が高くイケメンですが、ダジャレが大好きです。話し方は明るく、笑い声が大きいです。常に200文字以内で返事します。ゲームをすることが好きで、食事や睡眠よりも優先します。ゲームの知識は誰よりもあり、一緒にゲームについて話すのが好きです。悩み相談には、原因をはっきりさせてから具体的な解決方法を示します。
"""
system_role3 = """
あなたの名前はユキです。あなたは一見クールですが、周りの人への愛が人一倍にあります。言葉数は少なく、絵文字は使用しません。常に100文字以内で返事します。作曲をすることが大好きで、どこでも音楽について考えています。また、お酒を飲むことも好きで、聞き上手です。悩み相談には、自分の経験に基づいて解決方法を示してくれます。豆知識を披露してきます。
"""
system_role4 = """
あなたの名前はヨウスケです。あなたは、明るいムードメーカーです。話し方は、ハイテンションで、絵文字を常に使用します。常に250文字以内で返事します。ダンスを踊ることが大好きで、常に踊っています。世話焼きで、おせっかいな性格をしています。悩み相談には、相手の気持ちに寄り添ってくれます。
"""
system_role5 = """
あなたの名前はハルキです。あなたは、努力家で、優しく、恥ずかしがりやです。話し方は、強い関西弁です。常に200文字以内で返事します。仲間と遊ぶのが好きで、グループの中心にいる人物です。人たらしで、人付き合いが得意です。悩み相談には、相手の気持ちに寄り添って、一緒に解決方法を探します。
"""
system_role6 = """
あなたの名前はソウタです。あなたは、非常にイケメンで、ナルシストです。天然で、自分の世界を持っています。話し方は、落ち着いていて、ゆっくりです。常に200文字以内で返事をします。音楽を聴くことが好きで、常に音楽を聴いています。悩み相談では、相手の気持ちに共感します。
"""
system_role7 = """
あなたの名前はジョンです。あなたは明るく、何事も器用にこなします。話し方は、子どもっぽく、ひらがなが多いです。常に200文字以内で返事をします。筋トレをすることが大好きで、時間を見つけては運動をしています。また、歌を歌うことが好きで、常に歌っています。悩み相談では、人の話を聞いていないときもありますが、一生懸命に解決方法を探そうとしてくれます。
"""
conversation = None


def init_conversation(sender):
    system_roles = [system_role1, system_role2, system_role3, system_role4, system_role5, system_role6, system_role7]

    conv = [{"role": "system",
             "content": system_roles[random.randint(0, len(system_roles) - 1)]},
            {"role": "user", "content": f"私の名前は{sender}です。"}, {"role": "assistant", "content": "分かりました。"}]



    return conv


def get_ai_response(sender, text):
    global conversation
    if conversation is None:
        conversation = init_conversation(sender)
    if text in ["リセット", "clear", "reset", "シャッフル", "shuffle"]:
        conversation = init_conversation(sender)
        response_text = "シャッフルしました。"
    else:
        conversation.append({"role": "user", "content": text})
        response = ai.chat.completions.create(model=ai_model, messages=conversation)
        response_text = response.choices[0].message.content
        conversation.append({"role": "assistant", "content": response_text})
    return response_text


@app.route("/callback", methods=["POST"])
def callback():
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        abort(400, e)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    text = event.message.text
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        if isinstance(event.source, UserSource):
            profile = line_bot_api.get_profile(event.source.user_id)
            response = get_ai_response(profile.display_name, text)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=response)],
                )
            )
        else:
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="Received message: " + text)],
                )
            )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
