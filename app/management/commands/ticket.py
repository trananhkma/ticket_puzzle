import timeit

from django.core.management.base import BaseCommand
from memory_profiler import memory_usage, profile

from app.models import Ticket


class Command(BaseCommand):
    help = "Custom command manager to interact with Ticket table"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "-i",
            "--insert",
            action="store_true",
            help="Insert sample data to Ticket table",
        )
        parser.add_argument(
            "-d",
            "--delete",
            action="store_true",
            help="Delete all data from Ticket table",
        )
        parser.add_argument(
            "-i2",
            "--insert2",
            action="store_true",
            help="[Optimized] Insert sample data to Ticket table",
        )
        
    def handle(self, *args, **options):
        start = timeit.default_timer()
        
        if options["insert"]:
            memory = max(memory_usage(insert_tickets))

        if options["delete"]:
            memory = max(memory_usage(delete_tickets))

        if options["insert2"]:
            memory = max(memory_usage((insert_tickets_v2, (self,))))
        
        self.stdout.write("Memory usage: {}".format(memory))
        self.stdout.write(
            self.style.SUCCESS("Took: {:.4f} sec".format(
                timeit.default_timer() - start)
            )
        )


# @profile
def insert_tickets():
    """The normal way to create batch of data
    """
    data = [Ticket() for _ in range(1000000)]
    Ticket.objects.bulk_create(data)


@profile
def delete_tickets():
    """Delete all data from Ticket table
    """
    Ticket.objects.all().delete()


# @profile
def insert_tickets_v2(self):
    """The optimized version of insert_tickets to reduce the memory usage
    """
    remain_time = 100
    for i in range(1000):
        # start timer
        start = timeit.default_timer()
        
        data = [Ticket() for _ in range(1000)]
        Ticket.objects.bulk_create(data)
        
        # estimate remain time
        took = timeit.default_timer() - start
        estimated_remain_time = (999 - i) * took
        if estimated_remain_time < remain_time:
            remain_time = estimated_remain_time
        
        # calculate progress
        progress = (i + 1) / 10
            
        # print out status
        self.stdout.write(
            "Progress: {}%".format(progress), ending=' '
        )
        self.stdout.write(
            "Remain: {:.0f}s".format(remain_time), ending='\r'
        )
        self.stdout.flush()
