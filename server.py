from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask_cors import CORS
from model import detect_municipal_issue

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()
app = Flask(__name__)
CORS(app)

@app.route('/create-admin', methods=['POST'])
def create_admin():
    data = request.json
    print(data)

    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    department = data.get('department')
    role = data.get('role')
    createdBy = data.get('createdBy')

    try:
        # Create user in Firebase Auth
        user = auth.create_user(
            email=email,
            password=password
        )

        # Save user details in Firestore
        db.collection('users').document(user.uid).set({
            'email': email,
            'name': name,
            'department': department,
            'role': role, 
            'createdBy':createdBy
        })

        return jsonify({'message': 'Department Admin Created Successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
        
@app.route('/update-admin', methods=['PUT'])
def update_admin():
    data = request.json
    user_id = data.get('id')
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    department = data.get('department')
    role = data.get('role')

    try:
        # Update user in Firebase Auth
        if password:
            auth.update_user(
                user_id,
                email=email,
                password=password
            )
        else:
            auth.update_user(
                user_id,
                email=email
            )

        # Update user details in Firestore
        db.collection('users').document(user_id).update({
            'email': email,
            'name': name,
            'department': department,
            'role': role
        })

        return jsonify({'message': 'Department Admin Updated Successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/delete-admin/<user_id>', methods=['DELETE'])
def delete_admin(user_id):
    try:
        # Delete user from Firebase Auth
        auth.delete_user(user_id)

        # Delete user from Firestore
        db.collection('users').document(user_id).delete()

        return jsonify({'message': 'Department Admin Deleted Successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/analyze', methods=['POST'])
def analyze_image_url():
    data = request.get_json()
    image_url = data.get("image_url")

    if not image_url:
        return jsonify({"error": "Missing 'image_url' in request body"}), 400

    result = detect_municipal_issue(image_url)
    return jsonify(result), 200

    
if __name__ == '__main__':
    app.run(port=5000)
