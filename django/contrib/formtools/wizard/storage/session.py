from django.core.files.uploadedfile import UploadedFile
from django.contrib.formtools.wizard import storage


class SessionStorage(storage.BaseStorage):

    def __init__(self, prefix, request, file_storage=None, *args, **kwargs):
        super(SessionStorage, self).__init__(prefix)
        self.request = request
        self.file_storage = file_storage
        if self.prefix not in self.request.session:
            self.init_data()

    def init_data(self):
        self.request.session[self.prefix] = {
            self.step_key: None,
            self.step_data_key: {},
            self.step_files_key: {},
            self.extra_data_key: {},
        }
        self.request.session.modified = True
        return True

    def _get_current_step(self):
        return self.request.session[self.prefix][self.step_key]

    def _set_current_step(self, step):
        self.request.session[self.prefix][self.step_key] = step
        self.request.session.modified = True
        return True

    def _get_extra_data(self):
        return self.request.session[self.prefix][self.extra_data_key] or {}

    def _set_extra_data(self, extra_data):
        self.request.session[self.prefix][self.extra_data_key] = extra_data
        self.request.session.modified = True
        return True

    def get_step_data(self, step):
        return self.request.session[self.prefix][self.step_data_key].get(step, None)

    def set_step_data(self, step, cleaned_data):
        self.request.session[self.prefix][self.step_data_key][step] = cleaned_data
        self.request.session.modified = True

    def set_step_files(self, step, files):
        if files and not self.file_storage:
            raise storage.NoFileStorageConfigured

        if step not in self.request.session[self.prefix][self.step_files_key]:
            self.request.session[self.prefix][self.step_files_key][step] = {}

        for field, field_file in (files or {}).iteritems():
            tmp_filename = self.file_storage.save(field_file.name, field_file)
            file_dict = {
                'tmp_name': tmp_filename,
                'name': field_file.name,
                'content_type': field_file.content_type,
                'size': field_file.size,
                'charset': field_file.charset
            }
            self.request.session[self.prefix][self.step_files_key][step][field] = file_dict

        self.request.session.modified = True
        return True

    def get_step_files(self, step):
        session_files = self.request.session[self.prefix][self.step_files_key].get(step, {})

        if session_files and not self.file_storage:
            raise storage.NoFileStorageConfigured

        files = {}
        for field, field_dict in session_files.iteritems():
            files[field] = UploadedFile(
                file=self.file_storage.open(field_dict['tmp_name']),
                name=field_dict['name'],
                content_type=field_dict['content_type'],
                size=field_dict['size'],
                charset=field_dict['charset'])
        return files or None

    def reset(self):
        if self.file_storage:
            for step_fields in self.request.session[self.prefix][self.step_files_key].itervalues():
                for file_dict in step_fields.itervalues():
                    self.file_storage.delete(file_dict['tmp_name'])
        return self.init_data()
