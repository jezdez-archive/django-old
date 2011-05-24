from django.utils.functional import lazy_property

class BaseStorage(object):
    step_key = 'step'
    step_data_key = 'step_data'
    step_files_key = 'step_files'
    extra_data_key = 'extra_data'

    def __init__(self, prefix):
        self.prefix = 'wizard_%s' % prefix

    def _get_current_step(self):
        raise NotImplementedError

    def _set_current_step(self, step):
        raise NotImplementedError

    current_step = lazy_property(_get_current_step, _set_current_step)

    def _get_extra_data(self):
        raise NotImplementedError

    def _set_extra_data(self, extra_context):
        raise NotImplementedError

    extra_data = lazy_property(_get_extra_data, _set_extra_data)

    @property
    def current_step_data(self):
        return self.get_step_data(self.current_step)

    @property
    def current_step_files(self):
        return self.get_step_files(self.current_step)

    def get_step_data(self, step):
        raise NotImplementedError

    def set_step_data(self, step, cleaned_data):
        raise NotImplementedError

    def get_step_files(self, step):
        raise NotImplementedError

    def set_step_files(self, step, files):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def update_response(self, response):
        pass

    def init_data(self):
        pass
