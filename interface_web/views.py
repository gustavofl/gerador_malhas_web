from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import subprocess

def home(request):
    return render(request, 'home.html')

@csrf_exempt
def generate_meshes(request):
    if request.method == "POST":
        data = request.POST.get('data', '')

        # Execute o script local passando os dados
        result = subprocess.run(['/data/gerador_malhas/run.sh', data], capture_output=True, text=True)

        return JsonResponse({'output': result.stdout, 'error': result.stderr})
    return JsonResponse({'error': 'Invalid request method.'}, status=405)
