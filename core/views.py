from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.conf import settings
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
    if request.method == 'POST':
        try:
            from PIL import Image
            import torch
            import torchvision.transforms as transforms
            from ultralytics import YOLO
        except ImportError as exc:
            return JsonResponse({
                'success': False,
                'error': f'Missing CNN dependencies: {exc}. Install Pillow, torch, torchvision, ultralytics, and opencv-python to enable predictions.'
            })

        model_dir = settings.BASE_DIR / 'models'
        model_candidates = [
            model_dir / 'shark_species_cnn.pt',
            model_dir / 'best.pt',
        ]
        model_path = next((path for path in model_candidates if path.exists()), None)

        if model_path is None:
            return JsonResponse({
                'success': False,
                'error': 'No CNN model file found. Add models/shark_species_cnn.pt or models/best.pt.'
            })

        try:
            if 'image' not in request.FILES:
                return JsonResponse({'success': False, 'error': 'No image provided'})

            threshold_raw = request.POST.get('confidence_threshold', '0.25')
            try:
                confidence_threshold = float(threshold_raw)
            except (TypeError, ValueError):
                confidence_threshold = 0.25
            confidence_threshold = max(0.05, min(confidence_threshold, 0.95))

            image_file = request.FILES['image']
            image = Image.open(image_file).convert('RGB')

            if model_path.name == 'best.pt':
                model = YOLO(str(model_path))
                results = model.predict(source=image, device='cpu', conf=confidence_threshold, verbose=False)

                predictions = []
                if results and len(results[0].boxes) > 0:
                    top_boxes = results[0].boxes
                    for box in top_boxes:
                        class_id = int(box.cls.item())
                        confidence = float(box.conf.item())
                        # Normalized coordinates keep drawing aligned with any rendered image size.
                        x1, y1, x2, y2 = box.xyxyn[0].tolist()
                        predictions.append({
                            'species': model.names.get(class_id, f'Class {class_id}'),
                            'confidence': confidence,
                            'bbox': [x1, y1, x2, y2],
                        })

                predictions = sorted(predictions, key=lambda item: item['confidence'], reverse=True)[:5]

                return JsonResponse({
                    'success': True,
                    'predictions': predictions,
                    'threshold': confidence_threshold,
                })

            device = torch.device('cpu')
            model = torch.load(model_path, map_location=device, weights_only=False)
            model.eval()

            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])
            ])

            image_tensor = transform(image).unsqueeze(0).to(device)

            with torch.no_grad():
                outputs = model(image_tensor)

            shark_species = [
                'Great White Shark', 'Hammerhead Shark', 'Tiger Shark',
                'Bull Shark', 'Lemon Shark', 'Whale Shark', 'Nurse Shark',
                'Spinner Shark', 'Blacktip Shark', 'Sandbar Shark'
            ]

            probs = torch.nn.functional.softmax(outputs, dim=1)[0]
            top_5 = torch.topk(probs, min(5, len(shark_species)))

            predictions = []
            for conf, idx in zip(top_5.values, top_5.indices):
                confidence_value = float(conf)
                if confidence_value < confidence_threshold:
                    continue
                species_index = int(idx)
                if species_index < len(shark_species):
                    predictions.append({
                        'species': shark_species[species_index],
                        'confidence': confidence_value
                    })

            return JsonResponse({
                'success': True,
                'predictions': predictions,
                'threshold': confidence_threshold,
            })

        except Exception as exc:
            return JsonResponse({
                'success': False,
                'error': str(exc)
            })

    return render(request, "shark_cnn.html")
