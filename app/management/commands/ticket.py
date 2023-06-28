import timeit
from uuid import uuid4

from django.core.management.base import BaseCommand
from django.core.paginator import Paginator
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
        parser.add_argument(
            "-r",
            "--regenerate",
            action="store_true",
            help="Regenerate all tokens of Ticket table",
        )
        parser.add_argument(
            "-r2",
            "--regenerate2",
            action="store_true",
            help="[Optimized] Regenerate all tokens of Ticket table using iterator",
        )
        parser.add_argument(
            "-r3",
            "--regenerate3",
            action="store_true",
            help="[Optimized] Regenerate all tokens of Ticket table using paginator",
        )
        
    def handle(self, *args, **options):
        start = timeit.default_timer()
        
        if  options["delete"]:
            memory = max(memory_usage(self.delete_tickets))
        
        elif options["insert"]:
            memory = max(memory_usage(self.insert_tickets))

        elif options["insert2"]:
            memory = max(memory_usage(self.insert_tickets_v2))
            
        elif options["regenerate"]:
            memory = max(memory_usage(self.regenerate_tokens))
            
        elif options["regenerate2"]:
            memory = max(memory_usage(self.regenerate_tokens_v2))
            
        elif options["regenerate3"]:
            memory = max(memory_usage(self.regenerate_tokens_v3))
        
        self.stdout.write("Memory usage: {:.4f} MiB".format(memory))
        self.stdout.write(
            self.style.SUCCESS("Took: {:.4f} sec".format(
                timeit.default_timer() - start)
            )
        )

    @profile
    def delete_tickets(self):
        """Delete all data from Ticket table
        """
        Ticket.objects.all().delete()

    # @profile
    def insert_tickets(self):
        """The normal way to create batch of data
        """
        data = [Ticket() for _ in range(1000000)]
        Ticket.objects.bulk_create(data)

    # @profile
    def insert_tickets_v2(self):
        """The optimized version of insert_tickets to reduce the memory usage by generating smaller batch of data 
        """
        display_remain_time = 999999
        split_parts = 1000
        for i in range(split_parts):
            # start timer
            start = timeit.default_timer()
            
            data = [Ticket() for _ in range(1000)]
            Ticket.objects.bulk_create(data)
            
            # estimate remain time
            took = timeit.default_timer() - start
            estimated_remain_time = (split_parts - i) * took
            # avoid the display_remain_time keep fluctuating too much
            if estimated_remain_time < display_remain_time:
                display_remain_time = estimated_remain_time
            
            # calculate progress
            progress = (i + 1) / split_parts * 100
                
            # print out status
            self.stdout.write(
                "Progress: {:.1f}%".format(progress), ending=' '
            )
            self.stdout.write(
                "Remain: {:.0f}s".format(display_remain_time), ending='\r'
            )
            self.stdout.flush()

    # @profile
    def regenerate_tokens(self):
        """The normal way to update batch of data
        """
        tickets = Ticket.objects.all()
        for t in tickets:
            t.token = uuid4()
        
        Ticket.objects.bulk_update(tickets, ["token"])

    # @profile
    def regenerate_tokens_v2(self):
        """The optimized version of regenerate_tokens to reduce the memory usage by using iterator
        """
        display_remain_time = 999999

        total = Ticket.objects.count()
        chunk_size = 1000
        tickets = Ticket.objects.iterator(chunk_size=chunk_size)
        
        chunk = []
        for i, t in enumerate(tickets):
            if i % chunk_size == 0:
                # start timer
                start = timeit.default_timer()
            
            t.token = uuid4()
            chunk.append(t)

            if (i+1) % chunk_size == 0:
                # update data by chunk when chunk_size reaches 1000
                Ticket.objects.bulk_update(chunk, ["token"])
                chunk = []
                
                # estimate remain time
                took = timeit.default_timer() - start
                estimated_remain_time = (total - i) / chunk_size * took
                # avoid the display_remain_time keep fluctuating too much
                if estimated_remain_time < display_remain_time:
                    display_remain_time = estimated_remain_time
                
                # calculate progress
                progress = (i + 1) / total * 100
                
                # print out status
                self.stdout.write(
                    "Progress: {:.1f}%".format(progress), ending=" "
                )
                self.stdout.write(
                    "Remain: {:.0f}s".format(display_remain_time), ending="\r"
                )
                self.stdout.flush()

        # for remaining records if exist
        if chunk:
            Ticket.objects.bulk_update(chunk, ["token"])
        
    # @profile
    def regenerate_tokens_v3(self):
        """The optimized version of regenerate_tokens to reduce the memory usage by using Paginator
        """
        error_output = "./error.log"
        current_page = 1
        display_remain_time = 999999
        
        # restart near the point of previous interruption
        try:
            # check if error output exist and get the current_page
            with open(error_output) as f:
                number = f.read()
                current_page = int(number)
            
            # empty the error output
            with open(error_output, "w") as f:
                f.write("")
        except:
            # if the error output does not exist or the data inside is not a number, then do nothing
            pass

        try:
            tickets = Ticket.objects.all()
            paginator = Paginator(tickets, 1000)
            
            total_pages = paginator.num_pages
            
            for i in range(current_page, total_pages+1):
                current_page = i
                start = timeit.default_timer()
                
                page = paginator.page(i)
                chunk = []
                
                for ticket in page.object_list:
                    ticket.token = uuid4()
                    chunk.append(ticket)
            
                Ticket.objects.bulk_update(chunk, ["token"])
            
                
                # estimate remain time
                took = timeit.default_timer() - start
                estimated_remain_time = (total_pages - i + 1) * took
                # avoid the display_remain_time keep fluctuating too much
                if estimated_remain_time < display_remain_time:
                    display_remain_time = estimated_remain_time

                # calculate progress
                progress = i / total_pages * 100
                
                # print out status
                self.stdout.write(
                    "Progress: {:.1f}%".format(progress), ending=' '
                )
                self.stdout.write(
                    "Remain: {:.0f}s".format(display_remain_time), ending='\r'
                )
                self.stdout.flush()
            
        except (Exception, KeyboardInterrupt) as e:
            self.stdout.write(self.style.ERROR(str(e)))
            # write current_page to error output
            with open(error_output, "w") as f:
                f.write(str(current_page))
