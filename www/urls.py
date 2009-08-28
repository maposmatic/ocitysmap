from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

import maposmatic.views
import settings

urlpatterns = patterns('',
    (r'^$', maposmatic.views.index),
    (r'^smedia/(?P<path>.*)$',
     'django.views.static.serve',
     {'document_root': settings.LOCAL_MEDIA_PATH}),
    (r'^jobs/(?P<job_id>\d+)$', maposmatic.views.job),
    (r'^jobs/$', maposmatic.views.all_jobs),
)
