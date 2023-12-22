from flask import Flask, render_template, request, url_for
from werkzeug.utils import secure_filename
from flask_mysqldb import MySQL
from PIL import Image
from ultralytics import YOLO
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploadovane_slike' 
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MODEL_PATH = 'best-rucno.pt' 

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flaskdb'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


model = YOLO(MODEL_PATH)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def upload_file():
    return render_template('index.html')

@app.route('/uploader', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        #Procesiranje slike sa YOLOv8 modelom
        results = model(filepath)
        for r in results:
            im_array = r.plot()  # Plotovanje u BGR
            im = Image.fromarray(im_array[..., ::-1])  # Konvertuje u RGB for PIL
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_' + filename)
            im.save(output_path)  # Čuva sliku u folderu
        
        # Čuvanje informacija o slici u bazi podataka
        with app.app_context():
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO images (image_path, upload_date) VALUES (%s, CURRENT_TIMESTAMP)", (filename,))
            mysql.connection.commit()

        # Dohvatanje id-a poslednje dodate slike
            cur.execute("SELECT LAST_INSERT_ID()")
            image_id = cur.fetchone()['LAST_INSERT_ID()']

            # Dohvatanje komentara doktora i saveta iz HTML forme
            doctor_comments = request.form['doctorComments'] if 'doctorComments' in request.form else ''
            health_advice = request.form['advice'] if 'advice' in request.form else ''

            # Dodavanje informacija o dijagnozi u bazu podataka
            cur.execute("INSERT INTO diagnoses (doctor_comments, health_advice, image_id) VALUES (%s, %s, %s)",
                        (doctor_comments, health_advice, image_id))
            mysql.connection.commit()

            cur.close()



        return render_template('results.html', filename='uploadovane_slike/processed_' + filename)
    
  


if __name__ == '__main__':
    app.run(debug=True)
