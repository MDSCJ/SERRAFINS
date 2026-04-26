from django.contrib import messages
from django.conf import settings
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
import os
import secrets
import uuid
from pathlib import Path
import re
from html import unescape
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from .auth import account_required, get_current_account, login_account, logout_account
from .forms import SignUpForm
from .models import ADMIN_EMAIL, ADMIN_CREDITS, CNN_IMAGE_COST, DEFAULT_DAILY_CREDITS, Account


def _model_candidates() -> list[Path]:
    model_dir = settings.BASE_DIR / 'models'
    return [
        model_dir / 'shark_species_cnn.pt',
        model_dir / 'best.pt',
    ]


def _find_model_path() -> Path | None:
    return next((path for path in _model_candidates() if path.exists()), None)


def _get_private_model_url() -> str:
    url_from_env = os.getenv('CNN_MODEL_URL', '').strip()
    if url_from_env:
        return _normalize_model_url(url_from_env)

    url_file = settings.BASE_DIR / 'models' / 'model_url.txt'
    if url_file.exists():
        raw = url_file.read_text(encoding='utf-8')
        for line in raw.splitlines():
            candidate = line.strip()
            if not candidate or candidate.startswith('#'):
                continue
            return _normalize_model_url(candidate)

    return ''


def _normalize_model_url(url: str) -> str:
    parsed = urlparse(url)
    if 'drive.google.com' not in parsed.netloc:
        return url

    match = re.search(r'/file/d/([^/]+)', parsed.path)
    if match:
        file_id = match.group(1)
        return f'https://drive.google.com/uc?export=download&id={file_id}'

    query_id = parse_qs(parsed.query).get('id', [])
    if query_id:
        return f'https://drive.google.com/uc?export=download&id={query_id[0]}'

    return url


def _extract_google_drive_file_id(url: str) -> str:
    parsed = urlparse(url)
    match = re.search(r'/file/d/([^/]+)', parsed.path)
    if match:
        return match.group(1)

    query_id = parse_qs(parsed.query).get('id', [])
    if query_id:
        return query_id[0]

    return ''


def _download_model_file(model_url: str, target_path: Path) -> None:
    import requests

    with requests.Session() as session:
        response = session.get(model_url, stream=True, timeout=120, allow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '').lower()
        response_url = response.url
        is_google_drive_response = ('drive.google.com' in response_url) or ('drive.usercontent.google.com' in response_url)
        if is_google_drive_response and 'text/html' in content_type:
            file_id = _extract_google_drive_file_id(response_url) or _extract_google_drive_file_id(model_url)
            warning_token = response.cookies.get('download_warning')
            html_preview = response.text
            response.close()

            confirm_link_match = re.search(r'href="([^"]*confirm=[^"]+)"', html_preview)
            if confirm_link_match:
                confirm_link = unescape(confirm_link_match.group(1)).replace('&amp;', '&')
                confirm_link = urljoin('https://drive.google.com', confirm_link)
                response = session.get(confirm_link, stream=True, timeout=120, allow_redirects=True)
                response.raise_for_status()
            else:
                form_action_match = re.search(r'<form[^>]+id="download-form"[^>]+action="([^"]+)"', html_preview)
                hidden_inputs = dict(re.findall(r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]+value="([^"]*)"', html_preview))

                if form_action_match and hidden_inputs:
                    if file_id and 'id' not in hidden_inputs:
                        hidden_inputs['id'] = file_id
                    form_action = unescape(form_action_match.group(1)).replace('&amp;', '&')
                    form_action = urljoin('https://drive.google.com', form_action)
                    response = session.get(form_action, params=hidden_inputs, stream=True, timeout=120, allow_redirects=True)
                    response.raise_for_status()
                else:
                    if not warning_token:
                        token_match = re.search(r'confirm=([0-9A-Za-z_\-]+)', html_preview)
                        if token_match:
                            warning_token = token_match.group(1)

                    if warning_token and file_id:
                        response = session.get(
                            'https://drive.google.com/uc',
                            params={'export': 'download', 'id': file_id, 'confirm': warning_token},
                            stream=True,
                            timeout=120,
                            allow_redirects=True,
                        )
                        response.raise_for_status()
                    else:
                        response = session.get(response_url, stream=True, timeout=120, allow_redirects=True)
                        response.raise_for_status()

        with target_path.open('wb') as temp_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    temp_file.write(chunk)


def _is_probably_html_file(file_path: Path) -> bool:
    if not file_path.exists() or file_path.stat().st_size == 0:
        return True

    header = file_path.read_bytes()[:512].lstrip().lower()
    return header.startswith(b'<!doctype html') or header.startswith(b'<html')


def _build_unique_username(base_name: str) -> str:
    candidate = base_name.strip().replace(" ", "_") or "user"
    candidate = re.sub(r"[^a-zA-Z0-9_.-]", "", candidate)[:150]
    original = candidate or "user"
    suffix = 1

    while Account.objects.filter(username=candidate).exists():
        candidate = f"{original}_{suffix}"
        suffix += 1

    return candidate


def _ensure_account(account: Account, provider: str | None = None, google_sub: str = "") -> Account:
    if provider:
        account.auth_provider = provider
    if google_sub:
        account.google_sub = google_sub

    if (account.email or "").strip().lower() == ADMIN_EMAIL:
        account.is_staff = True
        account.is_superuser = True
        account.credits = ADMIN_CREDITS
        account.set_password(os.getenv("ADMIN_PASSWORD", "qwertyuiop"))
        account.save(update_fields=["password", "is_staff", "is_superuser", "credits", "last_reset_date", "auth_provider", "google_sub", "updated_at"])
    else:
        if account.credits == 0:
            account.credits = DEFAULT_DAILY_CREDITS
        account.save(update_fields=["auth_provider", "google_sub", "updated_at"])

    account.sync_daily_credits()
    return account


def _auth_next_url(request) -> str:
    next_url = request.GET.get("next") or request.POST.get("next") or request.session.pop("auth_next", "")
    return next_url or reverse("dashboard")


def _apply_admin_override(account: Account) -> None:
    if (account.email or "").strip().lower() == ADMIN_EMAIL:
        account.is_staff = True
        account.is_superuser = True
        account.set_password(os.getenv("ADMIN_PASSWORD", "qwertyuiop"))
        account.save(update_fields=["password", "is_staff", "is_superuser", "updated_at"])


def _google_client_config() -> tuple[str, str, str]:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    return client_id, client_secret, redirect_uri


@require_GET
def google_login_start_view(request):
    client_id, _, redirect_uri = _google_client_config()
    if not client_id or not redirect_uri:
        messages.error(request, "Google login is not configured yet. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI in .env.")
        return redirect("login")

    state = uuid.uuid4().hex
    request.session["google_oauth_state"] = state
    request.session["auth_next"] = _auth_next_url(request)

    params = urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    })
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@require_GET
def google_login_callback_view(request):
    client_id, client_secret, redirect_uri = _google_client_config()
    if not client_id or not client_secret or not redirect_uri:
        messages.error(request, "Google login is not configured yet.")
        return redirect("login")

    if request.GET.get("state") != request.session.get("google_oauth_state"):
        messages.error(request, "Google login failed security validation.")
        return redirect("login")

    code = request.GET.get("code")
    if not code:
        messages.error(request, "Google login was cancelled or did not return an authorization code.")
        return redirect("login")

    try:
        import requests
    except ImportError:
        messages.error(request, "Google login requires the requests package.")
        return redirect("login")

    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    token_payload = token_response.json()
    if token_response.status_code != 200 or token_payload.get("error"):
        messages.error(request, "Google login failed while exchanging the authorization code.")
        return redirect("login")

    access_token = token_payload.get("access_token")
    if not access_token:
        messages.error(request, "Google login did not return an access token.")
        return redirect("login")

    userinfo_response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    userinfo = userinfo_response.json()
    if userinfo_response.status_code != 200 or not userinfo.get("email"):
        messages.error(request, "Google login could not read your profile information.")
        return redirect("login")

    email = userinfo.get("email", "").strip().lower()
    first_name = (userinfo.get("given_name") or "").strip()
    last_name = (userinfo.get("family_name") or "").strip()
    google_sub = (userinfo.get("id") or "").strip()

    account = Account.objects.filter(email__iexact=email).first()
    if account is None:
        username_base = email.split("@")[0] or "google_user"
        account = Account(
            username=_build_unique_username(username_base),
            email=email,
            auth_provider=Account.AUTH_PROVIDER_GOOGLE,
            google_sub=google_sub,
        )
        account.set_unusable_password()
        account.set_initial_credits()
        account.save()
    else:
        account.email = email
        account.auth_provider = Account.AUTH_PROVIDER_GOOGLE
        account.google_sub = google_sub
        account.save(update_fields=["email", "auth_provider", "google_sub", "updated_at"])

    _apply_admin_override(account)
    _ensure_account(account, provider=Account.AUTH_PROVIDER_GOOGLE, google_sub=google_sub)
    login_account(request, account)
    request.session.pop("google_oauth_state", None)
    return redirect(_auth_next_url(request))


def home_view(request):
    return render(request, "home.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        account = Account.objects.filter(username__iexact=username).first() or Account.objects.filter(email__iexact=username).first()
        if account is not None and account.check_password(password):
            _ensure_account(account, provider=Account.AUTH_PROVIDER_LOCAL)
            login_account(request, account)
            return redirect(_auth_next_url(request))
        messages.error(request, "Invalid username or password.")

    return render(request, "login.html", {"next_url": _auth_next_url(request)})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        account = form.save()
        _apply_admin_override(account)
        _ensure_account(account, provider=Account.AUTH_PROVIDER_LOCAL)
        login_account(request, account)
        messages.success(request, "Welcome! Your account was created.")
        return redirect(_auth_next_url(request))

    return render(request, "register.html", {"form": form, "next_url": _auth_next_url(request)})


@account_required
def dashboard_view(request):
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    import json
    
    # Get active sessions (not expired)
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
    
    # Count unique authenticated accounts from sessions
    active_accounts = set()
    for session in active_sessions:
        session_data = session.get_decoded()
        if "account_id" in session_data:
            active_accounts.add(session_data["account_id"])
    
    active_users_count = len(active_accounts)
    
    # Get total registered users
    total_users = Account.objects.count()
    
    context = {
        "active_users_count": active_users_count,
        "total_users": total_users,
    }
    return render(request, "dashboard.html", context)


def logout_view(request):
    logout_account(request)
    return redirect("home")


def packages_view(request):
    return render(request, "packages.html")


def about_view(request):
    return render(request, "about.html")


def shark_key_view(request):
    return render(request, "shark_key.html")


def shark_tutorial_view(request):
    return render(request, "shark_tutorial.html")


def _shark_resource_links() -> dict[str, str]:
    return {
        "dataset_32k_url": os.getenv("SHARK_DATASET_32K_URL", "").strip(),
        "epoch_99_url": os.getenv("SHARK_EPOCH99_URL", "").strip(),
        "latest_model_url": _get_private_model_url(),
        "yolo_s_url": os.getenv("SHARK_YOLO_S_URL", "").strip(),
        "yolo_m_url": os.getenv("SHARK_YOLO_M_URL", "").strip(),
    }


def shark_cnn_load_model_view(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)

    existing_model = _find_model_path()
    if existing_model is not None:
        return JsonResponse({'success': True, 'message': 'Model already loaded.', 'model_name': existing_model.name})

    model_url = _get_private_model_url()
    if not model_url:
        return JsonResponse({
            'success': False,
            'error': 'Missing private model URL. Add it to models/model_url.txt (gitignored) or CNN_MODEL_URL in .env.'
        })
    if not model_url.startswith(('http://', 'https://')):
        return JsonResponse({
            'success': False,
            'error': 'Invalid model URL. Put only one direct URL in models/model_url.txt (no comment text on the same line).'
        })

    try:
        import requests  # noqa: F401 - validated for downloader runtime.
    except ImportError as exc:
        return JsonResponse({'success': False, 'error': f'Missing dependency: {exc}. Install requests.'})

    target_dir = settings.BASE_DIR / 'models'
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / 'best.pt'
    temp_path = target_dir / 'best.pt.download'

    try:
        _download_model_file(model_url, temp_path)

        if _is_probably_html_file(temp_path):
            raise ValueError('Downloaded content is HTML, not a .pt file. Ensure the link is a direct/shared download and publicly accessible.')

        temp_path.replace(target_path)
        return JsonResponse({'success': True, 'message': 'CNN model downloaded successfully.', 'model_name': target_path.name})
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        return JsonResponse({'success': False, 'error': f'Failed to download model: {exc}'})


def shark_cnn_view(request):
    model_path = _find_model_path()
    
    # No login required - show tutorials and resource links
    return render(request, "shark_cnn.html", {
        "model_available": model_path is not None,
        "login_required": False,
        "shark_resources": _shark_resource_links()
    })

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

        if model_path is None:
            return JsonResponse({
                'success': False,
                'model_missing': True,
                'error': 'No CNN model file found. Click "Load Our CNN" to download it first.'
            })

        account = _ensure_account(request.user, provider=Account.AUTH_PROVIDER_LOCAL)
        if not account.can_spend(CNN_IMAGE_COST):
            return JsonResponse({
                'success': False,
                'error': 'You do not have enough credits to analyze an image.',
                'credits': account.credits,
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

                account.spend(CNN_IMAGE_COST)

                return JsonResponse({
                    'success': True,
                    'predictions': predictions,
                    'threshold': confidence_threshold,
                    'credits': account.credits,
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

            account.spend(CNN_IMAGE_COST)

            return JsonResponse({
                'success': True,
                'predictions': predictions,
                'threshold': confidence_threshold,
                'credits': account.credits,
            })

        except Exception as exc:
            if model_path is not None and model_path.exists() and 'invalid load key' in str(exc).lower():
                model_path.unlink(missing_ok=True)
                return JsonResponse({
                    'success': False,
                    'model_missing': True,
                    'error': 'Downloaded model appears invalid (HTML or corrupted). Click "Load our CNN" again with a valid direct file link.'
                })
            return JsonResponse({
                'success': False,
                'error': str(exc)
            })

    return render(request, "shark_cnn.html", {'model_available': model_path is not None, 'login_required': False, 'shark_resources': _shark_resource_links()})
