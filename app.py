from flask import Flask, request, render_template
from Analyzer import Analyzer

app = Flask(__name__)
a = Analyzer()

@app.route('/', methods=['POST', 'GET'])
def init():
    word1 = ''
    word2 = ''
    res = ['', [], []]
    ans = ''
    if request.method == "POST":
        word1 = request.form['word1']
        word2 = request.form['word2']
        print(word1, word2)
        res = a.analyze(word1, word2, verbose=False)
        print(res)
        ans = ''
        if res[0]=='S':
            ans = 'суффиксальный'     
        elif res[0]=='PS':
            ans = 'приставочно-суффиксальный'
        elif res[0]=='P':
            ans = 'приставочный'
        elif res[0]=='BS':
            ans = 'бессуффиксный'
    return render_template('init.html', ans=ans, word1=word1, word1_lexemes=res[1], word2=word2, word2_lexemes=res[2])

@app.route('/info', methods=['POST', 'GET'])
def info():
    return render_template('info.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port='8001', debug=True)