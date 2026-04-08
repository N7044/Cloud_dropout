from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
import pandas as pd
import joblib
import os
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages

# 1. Load the ML Model when the server starts
# We use os.path to make sure Django always finds the file, no matter where it's hosted
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'best_dropout_model.pkl')
model = joblib.load(MODEL_PATH)


@login_required(login_url='login')
def student_dashboard(request):
    result = None
    
    # 2. If the user clicked the "Submit" button on the form...
    if request.method == 'POST':
        # Grab the data from the HTML form
        data = {
            'age': float(request.POST.get('age', 20)),
            'exam_season': float(request.POST.get('exam_season', 0)),
            'courses_enrolled': float(request.POST.get('courses_enrolled', 4)),
            'completed_assignments': float(request.POST.get('completed_assignments', 2)),
            'completion_rate': float(request.POST.get('completion_rate', 0.50)),
            'login_frequency': float(request.POST.get('login_frequency', 3.5)),
            'last_activity_days_ago': float(request.POST.get('last_activity_days_ago', 5)),
            'forum_posts_count': float(request.POST.get('forum_posts_count', 1))
        }
        
        # 3. Make the Prediction
        student_df = pd.DataFrame([data])
        prediction = model.predict(student_df)[0]
        probabilities = model.predict_proba(student_df)[0]
        risk_score = round(probabilities[1] * 100, 2)
        
        # 4. Package the result to send back to the HTML
        result = {
            "status": "High Risk of Dropout" if prediction == 1 else "Active & Engaged",
            "risk_score": f"{risk_score}%",
            "color": "red" if prediction == 1 else "green"
        }
        
    # 5. Render the page (passing the result if a prediction was made)
    return render(request, 'student_dashboard.html', {'result': result})



import io # <-- Add this to your imports at the very top of views.py

# ... (keep your existing student_dashboard function here) ...
@login_required(login_url='login')
def teacher_dashboard(request):
    results = None
    total_processed = 0
    error_msg = None
    
    if request.method == 'POST':
        # Check if a file was actually uploaded
        if 'csv_file' not in request.FILES:
            error_msg = "Please select a file to upload."
        else:
            csv_file = request.FILES['csv_file']
            
            # Security check: ensure it's a CSV
            if not csv_file.name.endswith('.csv'):
                error_msg = "Invalid file type. Please upload a .csv file."
            else:
                try:
                    # Read the uploaded file in memory
                    stream = io.StringIO(csv_file.read().decode("UTF8"), newline=None)
                    df = pd.read_csv(stream)
                    
                    # Separate Student IDs from the features
                    if 'student_id' in df.columns:
                        student_ids = df['student_id'].tolist()
                        features_df = df.drop(columns=['student_id'])
                    else:
                        student_ids = [f"Student_{i+1}" for i in range(len(df))]
                        features_df = df
                        
                    # 🚀 Run Bulk Predictions
                    predictions = model.predict(features_df)
                    probabilities = model.predict_proba(features_df)
                    
                    # Package the results into a list of dictionaries for the HTML
                    results = []
                    for i in range(len(predictions)):
                        risk_score = round(probabilities[i][1] * 100, 2)
                        results.append({
                            "student_id": student_ids[i],
                            "status": "High Risk" if predictions[i] == 1 else "Active",
                            "risk_score": f"{risk_score}%",
                            "is_danger": bool(predictions[i] == 1)
                        })
                    
                    total_processed = len(results)
                    
                except Exception as e:
                    error_msg = f"Error processing file: {str(e)}"

    # Send the results (if any) to the teacher dashboard template
    context = {
        'results': results,
        'total_processed': total_processed,
        'error_msg': error_msg
    }
    return render(request, 'teacher_dashboard.html', context)



def auth_view(request):
    # If they are already logged in, send them straight to their dashboard!
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Teacher').exists():
            return redirect('teacher_dashboard')
        return redirect('student_dashboard')

    if request.method == 'POST':
        action = request.POST.get('action') # Are they trying to log in or sign up?

        # --- LOGIN LOGIC ---
        if action == 'login':
            u = request.POST.get('username')
            p = request.POST.get('password')
            user = authenticate(request, username=u, password=p)
            
            if user is not None:
                login(request, user)
                if user.groups.filter(name='Teacher').exists():
                    return redirect('teacher_dashboard')
                return redirect('student_dashboard')
            else:
                messages.error(request, "Invalid username or password.")

        # --- SIGNUP LOGIC ---
        elif action == 'signup':
            u = request.POST.get('username')
            p = request.POST.get('password')
            role = request.POST.get('role')

            if User.objects.filter(username=u).exists():
                messages.error(request, "Username already exists. Please choose another.")
            else:
                # Create the secure user
                user = User.objects.create_user(username=u, password=p)
                
                # Assign them to the Student or Teacher group
                group_name = 'Teacher' if role == 'teacher' else 'Student'
                group, created = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)

                # Log them in automatically
                login(request, user)
                if role == 'teacher':
                    return redirect('teacher_dashboard')
                return redirect('student_dashboard')

    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')