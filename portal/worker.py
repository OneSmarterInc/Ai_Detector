import logging
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone
from .models import ScanJob
from .analysis import percentage_breakdown
EXECUTOR=ThreadPoolExecutor(max_workers=1,thread_name_prefix='inspector')
logger=logging.getLogger(__name__)

def update(job_id,**values):
    ScanJob.objects.filter(id=job_id).update(updated=timezone.now(),**values)

def run_job(job_id):
    close_old_connections()
    try:
        import inspector
        job=ScanJob.objects.get(id=job_id)
        folder=settings.DATA_ROOT/'jobs'/str(job.id)
        assets=folder/'assets';assets.mkdir(exist_ok=True)
        results=[];counter=[0]
        for i,item in enumerate(job.files,1):
            update(job_id,status='running',progress=f'Checking {i} of {len(job.files)}: {item["name"]}')
            try:
                result=inspector.inspect_file(folder/'uploads'/item['stored'],assets,counter)
                result['file']=item['name']
                for picture in result.get('images',[]):
                    if picture.get('source')==item['stored']:picture['source']=item['name']
                result['breakdown']=percentage_breakdown(result.get('text',{}).get('ai_detection'))
            except Exception:
                logger.exception('File check failed for job %s, file %s',job_id,item['stored'])
                result={'file':item['name'],'status':'failed','error':'This file could not be read. Open it in its usual app, save a fresh unlocked copy, and try again.'}
            results.append(result)
            update(job_id,results=results)
        update(job_id,status='complete',progress='Your report is ready.',results=results)
    except Exception:
        logger.exception('Job %s failed',job_id)
        update(job_id,status='failed',progress='Scan stopped',error='This scan could not finish. Try again or restart the portal.')
    finally:close_old_connections()

def submit_job(job_id):EXECUTOR.submit(run_job,job_id)

def recover_interrupted_jobs():
    ScanJob.objects.filter(status__in=['queued','running']).update(status='failed',error='The portal restarted before this scan finished. Please upload these files again.',progress='Scan interrupted')
