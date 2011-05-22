from django.core.files.uploadedfile import UploadedFile

from django.contrib.formtools.wizard.storage import (BaseStorage,
                                                     NoFileStorageConfigured)

class SessionStorage(BaseStorage):
    step_session_key = 'step'
    step_data_session_key = 'step_data'
    step_files_session_key = 'step_files'
    extra_data_session_key = 'extra_data'

    def __init__(self, prefix, request, file_storage=None, *args, **kwargs):
        super(SessionStorage, self).__init__(prefix)
        self.request = request
        self.file_storage = file_storage
        if self.prefix not in self.request.session:
            self.init_storage()

    def init_storage(self):
        self.request.session[self.prefix] = {
            self.step_session_key: None,
            self.step_data_session_key: {},
            self.step_files_session_key: {},
            self.extra_data_session_key: {},
        }
        self.request.session.modified = True
        return True

    def get_current_step(self):
        return self.request.session[self.prefix][self.step_session_key]

    def set_current_step(self, step):
        self.request.session[self.prefix][self.step_session_key] = step
        self.request.session.modified = True
        return True

    def get_step_data(self, step):
        return self.request.session[self.prefix][self.step_data_session_key].get(step, None)

    def get_current_step_data(self):
        return self.get_step_data(self.get_current_step())

    def set_step_data(self, step, cleaned_data):
        self.request.session[self.prefix][self.step_data_session_key][step] = cleaned_data
        self.request.session.modified = True
        return True

    def set_step_files(self, step, files):
        if files and not self.file_storage:
            raise NoFileStorageConfigured

        if step not in self.request.session[self.prefix][self.step_files_session_key]:
            self.request.session[self.prefix][self.step_files_session_key][step] = {}

        for field, field_file in (files or {}).iteritems():
            tmp_filename = self.file_storage.save(field_file.name, field_file)
            file_dict = {
                'tmp_name': tmp_filename,
                'name': field_file.name,
                'content_type': field_file.content_type,
                'size': field_file.size,
                'charset': field_file.charset
            }
            self.request.session[self.prefix][self.step_files_session_key][step][field] = file_dict

        self.request.session.modified = True
        return True

    def get_current_step_files(self):
        return self.get_step_files(self.get_current_step())

    def get_step_files(self, step):
        session_files = self.request.session[self.prefix][self.step_files_session_key].get(step, {})

        if session_files and not self.file_storage:
            raise NoFileStorageConfigured

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

    def get_extra_data(self):
        return self.request.session[self.prefix][self.extra_data_session_key] or {}

    def set_extra_data(self, extra_data):
        self.request.session[self.prefix][self.extra_data_session_key] = extra_data
        self.request.session.modified = True
        return True

    def reset(self):
        if self.file_storage:
            for step_fields in self.request.session[self.prefix][self.step_files_session_key].itervalues():
                for file_dict in step_fields.itervalues():
                    self.file_storage.delete(file_dict['tmp_name'])
        return self.init_storage()

    def update_response(self, response):
        return response
