# Create your views here.

from django.forms import ModelForm
from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponseRedirect
from www.maposmatic.models import MapRenderingJob

class MapRenderingJobForm(ModelForm):
    class Meta:
        model = MapRenderingJob
        fields = ('maptitle', 'administrative_city', 'lat_upper_left', 'long_upper_left',
                  'lat_bottom_right', 'long_bottom_right')

def index(request):
    if request.method == 'POST':
        print 'POST'
        form = MapRenderingJobForm(request.POST)
        if form.is_valid():
            print 'form_valid'
            job = MapRenderingJob()
            job.maptitle = form.cleaned_data['maptitle']
            job.administrative_city = form.cleaned_data['administrative_city']
            job.lat_upper_left = form.cleaned_data['lat_upper_left']
            job.long_upper_left = form.cleaned_data['long_upper_left']
            job.lat_bottom_right = form.cleaned_data['lat_bottom_right']
            job.long_bottom_right = form.cleaned_data['long_bottom_right']
            job.status = 0 # Submitted
            job.submitterip = request.META['REMOTE_ADDR']
            job.index_queue_at_submission = 0
            job.save()

            return HttpResponseRedirect('/jobs/%d' % job.id)
    else:
        form = MapRenderingJobForm()
    return render_to_response('maposmatic/index.html',
                              { 'form' : form })

def job(request, job_id):
    job = get_object_or_404(MapRenderingJob, id=job_id)
    return render_to_response('maposmatic/job.html',
                              { 'job' : job })

def all_jobs(request):
    jobs = MapRenderingJob.objects.all()
    print jobs
    return render_to_response('maposmatic/all_jobs.html',
                              { 'jobs' : jobs })
