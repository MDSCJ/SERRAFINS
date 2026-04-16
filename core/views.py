from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import JsonResponse

from .forms import SignUpForm


def home_view(request):
    return render(request, "index.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        messages.error(request, "Invalid username or password.")

    return render(request, "login.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! Your account was created.")
        return redirect("dashboard")

    return render(request, "register.html", {"form": form})


@login_required
def dashboard_view(request):
    return render(request, "dashboard.html")


def packages_view(request):
    return render(request, "packages.html")


def about_view(request):
    return render(request, "about.html")


def shark_key_view(request):
    return render(request, "shark_key.html")


def shark_cnn_view(request):
    import json
    import os
    from PIL import Image
    import torch
    import torchvision.transforms as transforms
    
    if request.method == 'POST':
        # Check if model file exists
        model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'shark_species_cnn.pt')
        
        if not os.path.exists(model_path):
            return JsonResponse({
                'success': False,
                'error': f'Model file not found at {model_path}. Please upload your shark_species_cnn.pt file.'
            })
        
        try:
            # Handle image upload
            if 'image' not in request.FILES:
                return JsonResponse({'success': False, 'error': 'No image provided'})
            
            image_file = request.FILES['image']
            image = Image.open(image_file).convert('RGB')
            
            # Load model
            device = torch.device('cpu')
            model = torch.load(model_path, map_location=device)
            model.eval()
            
            # Preprocess image
            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])
            ])
            
            image_tensor = transform(image).unsqueeze(0).to(device)
            
            # Make prediction
            with torch.no_grad():
                outputs = model(image_tensor)
            
            # Example shark species
            shark_species = [
                'Great White Shark', 'Hammerhead Shark', 'Tiger Shark',
                'Bull Shark', 'Lemon Shark', 'Whale Shark', 'Nurse Shark',
                'Spinner Shark', 'Blacktip Shark', 'Sandbar Shark'
            ]
            
            # Convert outputs to probabilities
            probs = torch.nn.functional.softmax(outputs, dim=1)[0]
            top_5 = torch.topk(probs, min(5, len(shark_species)))
            
            predictions = []
            for i, (conf, idx) in enumerate(zip(top_5.values, top_5.indices)):
                if idx < len(shark_species):
                    predictions.append({
                        'species': shark_species[idx],
                        'confidence': float(conf)
                    })
            
            return JsonResponse({
                'success': True,
                'predictions': predictions
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return render(request, "shark_cnn.html")
