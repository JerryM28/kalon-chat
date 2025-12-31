# Deploy ke Render.com

## Step 1: Buat Akun GitHub
1. Buka https://github.com
2. Klik "Sign up" → Isi email, password
3. Verifikasi email

## Step 2: Upload Code ke GitHub
1. Login GitHub
2. Klik "+" (pojok kanan atas) → "New repository"
3. Nama: `kalon-chat`
4. Pilih "Public"
5. Klik "Create repository"
6. Upload semua file dari folder ini:
   - app.py
   - requirements.txt
   - render.yaml

## Step 3: Deploy ke Render
1. Buka https://render.com
2. Klik "Get Started for Free"
3. Pilih "Sign up with GitHub"
4. Authorize Render
5. Klik "New +" → "Web Service"
6. Connect repository `kalon-chat`
7. Settings:
   - Name: kalon-chat (atau nama lain)
   - Region: Singapore (terdekat)
   - Branch: main
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
8. Klik "Create Web Service"
9. Tunggu 2-3 menit

## Step 4: Akses!
Setelah deploy selesai, dapat URL seperti:
`https://kalon-chat.onrender.com`

Bisa diakses dari mana saja! 🎉