from django.http import HttpResponse

def home(request):
    return HttpResponse("Sniffer App is Running!")
