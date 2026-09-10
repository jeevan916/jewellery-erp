from django.http import HttpResponse
class SimpleCORSMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        if request.method=='OPTIONS': response=HttpResponse(status=204)
        else: response=self.get_response(request)
        response['Access-Control-Allow-Origin']='*'
        response['Access-Control-Allow-Headers']='Authorization, Content-Type'
        response['Access-Control-Allow-Methods']='GET, POST, PUT, PATCH, DELETE, OPTIONS'
        return response
