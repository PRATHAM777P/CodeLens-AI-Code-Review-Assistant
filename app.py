from flask import Flask, request, jsonify
from analysis import analyze_code

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', 'python')
    prompt = data.get('prompt', '')
    result = analyze_code(code, language=language, prompt=prompt)
    return jsonify(result)

if __name__ == '__main__':
    app.run()