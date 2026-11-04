import json,mimetypes,shutil
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse,FileResponse,Http404
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods,require_GET
from .models import ScanJob
from .worker import submit_job
from .uploads import MAX_FILE,MAX_BATCH

def owner(request):
    if not request.session.session_key:request.session.create()
    return request.session.session_key

def payload(job,details=True):
    data=dict(id=str(job.id),status=job.status,progress=job.progress,created=job.created.isoformat(),
              files=[{'name':x['name'],'size':x['size']} for x in job.files],error=job.error)
    if details:data['results']=job.results
    return data

@require_GET
def info(request):
    import ai_detector,inspector
    return JsonResponse(dict(csrf_token=get_token(request),model=ai_detector.MODEL_NAME,model_ready=ai_detector.installed(),
        extensions=sorted(inspector.SUPPORTED),max_file_bytes=MAX_FILE,max_batch_bytes=MAX_BATCH,max_files=10,
        minimum_words=100,max_characters=200000,max_sections=12,pdf_pages=300,image_pixels=40000000,
        limits_text=(settings.BASE_DIR/'FILE-LIMITS.txt').read_text(encoding='utf-8')))

@require_http_methods(['GET','POST'])
def jobs(request):
    key=owner(request)
    if request.method=='GET':return JsonResponse({'jobs':[payload(j,False) for j in ScanJob.objects.filter(owner=key).order_by('-created')[:20]]})
    import inspector
    files=request.FILES.getlist('files')
    if getattr(request,'upload_error',None):return JsonResponse({'error':request.upload_error},status=413)
    text=request.POST.get('text','')
    if files and text:return JsonResponse({'error':'Choose files or paste text, not both in one scan.'},status=400)
    if not files and not text.strip():return JsonResponse({'error':'Choose a file or paste some English writing.'},status=400)
    if len(files)>10:return JsonResponse({'error':'Choose up to 10 files per batch.'},status=400)
    if len(text)>200000:return JsonResponse({'error':'Paste up to 200,000 characters.'},status=400)
    if any(x.size>MAX_FILE for x in files) or sum(x.size for x in files)>MAX_BATCH:return JsonResponse({'error':'Use files up to 100 MB each and 500 MB per batch.'},status=413)
    if any(Path(x.name).suffix.lower() not in inspector.SUPPORTED for x in files):return JsonResponse({'error':'One of these file types is not supported. Open File limits for the full list.'},status=400)
    if ScanJob.objects.filter(status__in=['queued','running']).count()>=5:return JsonResponse({'error':'There are several scans waiting. Wait for one to finish, then try again.'},status=429)
    job=ScanJob.objects.create(owner=key)
    folder=settings.DATA_ROOT/'jobs'/str(job.id);uploads=folder/'uploads'
    items=[]
    try:
        uploads.mkdir(parents=True)
        for i,file in enumerate(files,1):
            stored=str(i)+Path(file.name).suffix.lower()
            with (uploads/stored).open('wb') as stream:
                for block in file.chunks():stream.write(block)
            items.append({'name':Path(file.name.replace('\\','/')).name[:240],'stored':stored,'size':file.size})
        if text:
            data=text.encode('utf-8');(uploads/'1.txt').write_bytes(data)
            items=[{'name':'Pasted text.txt','stored':'1.txt','size':len(data)}]
        job.files=items;job.save(update_fields=['files'])
        submit_job(job.id)
    except Exception:
        if folder.exists() and folder.resolve().parent==(settings.DATA_ROOT/'jobs').resolve():shutil.rmtree(folder,ignore_errors=True)
        job.delete()
        return JsonResponse({'error':'Could not save this scan. Check free disk space and try again.'},status=500)
    return JsonResponse(payload(job),status=202)

def owned_job(request,job_id):return get_object_or_404(ScanJob,id=job_id,owner=owner(request))

@require_http_methods(['GET','DELETE'])
def job_detail(request,job_id):
    job=owned_job(request,job_id)
    if request.method=='GET':return JsonResponse(payload(job))
    if job.status in ['queued','running']:return JsonResponse({'error':'Wait for this scan to finish before deleting it.'},status=409)
    folder=settings.DATA_ROOT/'jobs'/str(job.id)
    if folder.exists() and folder.resolve().parent==(settings.DATA_ROOT/'jobs').resolve():shutil.rmtree(folder)
    job.delete();return JsonResponse({'deleted':True})

@require_GET
def report_download(request,job_id):
    job=owned_job(request,job_id)
    response=JsonResponse(payload(job),json_dumps_params={'ensure_ascii':False,'indent':2})
    response['Content-Disposition']='attachment; filename="inspection-report.json"'
    return response

@require_GET
def asset(request,job_id,name):
    job=owned_job(request,job_id)
    allowed={Path(v['file']).name for r in job.results for image in r.get('images',[]) for v in image.get('visuals',[])}
    if name not in allowed:raise Http404
    path=settings.DATA_ROOT/'jobs'/str(job.id)/'assets'/name
    if not path.is_file():raise Http404
    return FileResponse(path.open('rb'),content_type='image/png')

@require_GET
def frontend(request,path=''):
    if path.startswith('api/'):return JsonResponse({'error':'Endpoint not found.'},status=404)
    root=settings.FRONTEND_DIST.resolve()
    target=(root/(path or 'index.html')).resolve()
    if not target.is_relative_to(root) or not target.is_file():raise Http404('Build the React frontend first.')
    response=FileResponse(target.open('rb'),content_type=mimetypes.guess_type(str(target))[0] or 'application/octet-stream')
    response['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'"
    return response
