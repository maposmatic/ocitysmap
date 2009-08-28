from django.db import models
from datetime import datetime

class MapRenderingJobManager(models.Manager):
    def to_render(self):
        return MapRenderingJob.objects.filter(status=0).order_by('submission_time')

class MapRenderingJob(models.Model):

    STATUS_LIST = (
        (0, 'Submitted'),
        (1, 'In progress'),
        (2, 'Done'),
        )

    maptitle = models.CharField(max_length=256)
    administrative_city = models.CharField(max_length=256, blank=True, null=True)
    lat_upper_left = models.FloatField(blank=True, null=True)
    lon_upper_left = models.FloatField(blank=True, null=True)
    lat_bottom_right = models.FloatField(blank=True, null=True)
    lon_bottom_right = models.FloatField(blank=True, null=True)
    status = models.IntegerField(choices=STATUS_LIST)
    submission_time = models.DateTimeField(auto_now_add=True)
    startofrendering_time = models.DateTimeField(null=True)
    endofrendering_time = models.DateTimeField(null=True)
    resultmsg = models.CharField(max_length=256, null=True)
    submitterip = models.IPAddressField()
    index_queue_at_submission = models.IntegerField()

    objects = MapRenderingJobManager()

    def maptitle_computized(self):
        return "'%s'" % self.maptitle

    def files_prefix(self):
        return "%d-%s-%s" % (self.id,
                             self.startofrendering_time.strftime("%Y-%m-%d-%H:%M"),
                             self.maptitle_computized())
