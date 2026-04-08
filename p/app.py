from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import joblib
import io

app = Flask(__name__)
CORS(app) 

# Load the trained EdTech model
print("Loading EdTech Prediction Model...")
model = joblib.load('best_dropout_model.pkl')

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "Cloud API is Online! Ready for Students and Teachers."})

# ==========================================
# 🎓 STUDENT PORTAL: Single Prediction
# ==========================================
@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        student_df = pd.DataFrame([data])
        
        prediction = model.predict(student_df)[0]
        probabilities = model.predict_proba(student_df)[0]
        risk_score = round(probabilities[1] * 100, 2)
        
        status = "High Risk of Dropout" if prediction == 1 else "Active & Engaged"
        
        return jsonify({
            "status": status,
            "risk_score": f"{risk_score}%"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ==========================================
# 👨‍🏫 TEACHER PORTAL: Bulk CSV Upload
# ==========================================
@app.route('/predict_bulk', methods=['POST'])
def predict_bulk():
    try:
        # 1. Check if a file was uploaded
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
            
        file = request.files['file']
        
        if not file.filename.endswith('.csv'):
            return jsonify({"error": "Please upload a .csv file"}), 400

        # 2. Read the uploaded CSV file into a Pandas DataFrame
        # We use io.StringIO to read the file directly from memory (Cloud best practice!)
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        df = pd.read_csv(stream)
        
        # 3. Save a copy of the student IDs (if they exist) so we know who is who, 
        # but drop them from the data we send to the model
        if 'student_id' in df.columns:
            student_ids = df['student_id'].tolist()
            features_df = df.drop(columns=['student_id'])
        else:
            student_ids = [f"Student_{i+1}" for i in range(len(df))]
            features_df = df
            
        # 4. Make predictions for EVERYONE at once (Bulk Processing)
        predictions = model.predict(features_df)
        probabilities = model.predict_proba(features_df)
        
        # 5. Format the results into a list
        results = []
        for i in range(len(predictions)):
            risk_score = round(probabilities[i][1] * 100, 2)
            results.append({
                "student_id": student_ids[i],
                "status": "High Risk" if predictions[i] == 1 else "Active",
                "risk_score": f"{risk_score}%",
                "needs_intervention": bool(predictions[i] == 1)
            })
            
        return jsonify({"total_processed": len(results), "results": results})

    except Exception as e:
        return jsonify({"error": f"Failed to process file: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)