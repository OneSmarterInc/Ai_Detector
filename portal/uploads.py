from django.core.files.uploadhandler import FileUploadHandler,StopUpload
MAX_FILE=100*1024*1024
MAX_BATCH=500*1024*1024
class LimitedUploadHandler(FileUploadHandler):
    def __init__(self,request=None):
        super().__init__(request);self.total=0;self.current=0
    def new_file(self,*args,**kwargs):
        super().new_file(*args,**kwargs);self.current=0
    def receive_data_chunk(self,raw_data,start):
        self.current+=len(raw_data);self.total+=len(raw_data)
        if self.current>MAX_FILE or self.total>MAX_BATCH:
            self.request.upload_error='Use files up to 100 MB each and 500 MB per batch.'
            raise StopUpload(connection_reset=True)
        return raw_data
    def file_complete(self,file_size):return None
