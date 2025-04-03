# Create a file like middlewares.py in your app

class BlockBannedIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Check if IP is banned (adjust this based on your model structure)
        from ecom.models import BannedIP
        print(client_ip)
        if BannedIP.objects.filter(ip_address=client_ip).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Your IP address is banned")
            
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip