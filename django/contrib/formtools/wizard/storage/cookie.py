from django.core.exceptions import SuspiciousOperation
from django.core.signing import BadSignature
from django.core.files.uploadedfile import UploadedFile
from django.utils import simplejson as json

from django.contrib.formtools.wizard import storage




class CookieStorage(storage.BaseStorage):
    encoder = json.JSONEncoder(separators=(',', ':'))

    def __init__(self, prefix, request, file_storage, *args, **kwargs):
        super(CookieStorage, self).__init__(prefix)
        self.file_storage = file_storage
        self.request = request
        self.data = self.load_data()
        if self.data is None:
            self.init_data()

    def init_data(self):
        self.data = {
            self.step_key: None,
            self.step_data_key: {},
            self.step_files_key: {},
            self.extra_data_key: {},
        }
        return True

    def reset(self):
        return self.init_data()

    def load_data(self):
        try:
            data = self.request.get_signed_cookie(self.prefix)
        except KeyError:
            data = None
        except BadSignature:
            raise SuspiciousOperation('FormWizard cookie manipulated')
        if data is None:
            return None
        return json.loads(data, cls=json.JSONDecoder)

    def _get_current_step(self):
        return self.data[self.step_key]

    def _set_current_step(self, step):
        self.data[self.step_key] = step

    def _get_extra_data(self):
        return self.data[self.extra_data_key] or {}

    def _set_extra_data(self, extra_data):
        self.data[self.extra_data_key] = extra_data

    def get_step_data(self, step):
        return self.data[self.step_data_key].get(step, None)

    def set_step_data(self, step, cleaned_data):
        self.data[self.step_data_key][step] = cleaned_data

    def set_step_files(self, step, files):
        if files and not self.file_storage:
            raise storage.NoFileStorageConfigured

        if step not in self.data[self.step_files_key]:
            self.data[self.step_files_key][step] = {}

        for field, field_file in (files or {}).iteritems():
            tmp_filename = self.file_storage.save(field_file.name, field_file)
            file_dict = {
                'tmp_name': tmp_filename,
                'name': field_file.name,
                'content_type': field_file.content_type,
                'size': field_file.size,
                'charset': field_file.charset
            }
            self.data[self.step_files_key][step][field] = file_dict
        return True

    def get_step_files(self, step):
        session_files = self.data[self.step_files_key].get(step, {})

        if session_files and not self.file_storage:
            raise storage.NoFileStorageConfigured

        files = {}
        for field, field_dict in session_files.iteritems():
            files[field] = UploadedFile(
                file=self.file_storage.open(field_dict['tmp_name']),
                name=field_dict['name'],
                content_type=field_dict['content_type'],
                size=field_dict['size'],
                charset=field_dict['charset'],
            )
        return files or None

    def update_response(self, response):
        if len(self.data) > 0:
            response.set_signed_cookie(self.prefix, self.encoder.encode(self.data))
        else:
            response.delete_cookie(self.prefix)
        return response
