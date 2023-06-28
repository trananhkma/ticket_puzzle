# Ticket Puzzle

A database table/model "Ticket" has 1 million rows. The table has a "token" column that holds a random unique UUID value for each row, determined by Django/Python logic at the time of creation.

Due to a data leak, the candidate should write a django management command to iterate over every Ticket record to regenerate the unique UUID value.

The command should inform the user of progress as the script runs and estimates the amount of time remaining.

The script should also be sensitive to the potentially limited amount of server memory and avoid loading the full dataset into memory all at once, and show an understanding of Django ORM memory usage and query execution.

Finally, the script should ensure that if it is interrupted that it should save progress and restart near the point of interruption so that it does not need to process the entire table from the start.

Please use Django / Python for your solution. The logic and thought process demonstrated are the most important considerations rather than truly functional code, however code presentation is important as well as the technical aspect. If you cannot settle on a single perfect solution, you may also discuss alternative solutions to demonstrate your understanding of potential trade-offs as you encounter them. Of course if you consider a solution is too time consuming you are also welcome to clarify or elaborate on potential improvements or multiple solution approaches conceptually to demonstrate understanding and planned solution.

## I. Setting up

1. Create .env file and modify variables if necessary

    ```bash
    cp .env.example .env
    ```

2. Build containers

    ```bash
    docker-compose up -d --build
    ```

3. Run migrate database

    ```bash
    docker-compose run app python manage.py migrate
    ```

4. Access the `app` container

    ```bash
    docker-compose exec app bash
    ```

5. Run commands to add sample data to database

    ```bash
    python manage.py ticket --insert2
    ```

6. Test the regenerate token command

    ```bash
    python manage.py ticket --regenerate3
    ```

## II. Description

There are three main custom management commands: `insert`, `delete`, `regenerate`, located at `app/management/commands/ticket.py`

### 1. Memory measurement

The project uses `memory-profiler` package to measure the memory usage of each function. Simply adding `@profile` decorator:

```python
@profile
def delete_tickets():
    """Delete all data from Ticket table
    """
    Ticket.objects.all().delete()
```

Then the `delete` command will display:

```bash
root@ee2f26ee92c6:/code# python manage.py ticket --delete
Filename: /code/app/management/commands/ticket.py

Line #    Mem usage    Increment  Occurrences   Line Contents
=============================================================
    89     41.7 MiB     41.7 MiB           1   @profile
    90                                         def delete_tickets():
    91                                             """Delete all data from Ticket table
    92                                             """
    93     43.0 MiB      1.3 MiB           1       Ticket.objects.all().delete()


Memory usage: 42.9805 MiB
Took: 1.0716 sec
```

The output shows the initial `Memory usage` is `41.7 MiB`. And the line `93` for deleting operation took `1.3 MiB` more.

This `@profile` decorator is really good for measuring the memory usage line by line. But it has a downside that it affects run-time, depends on the amount of lines and for loops in the function.

If we apply `@profile` for `insert` / `regenerate` functions, then the run-time is significant increased.

So to measure the memory usage of these functions, we can use `memory_usage`:

```python
memory_usage(insert_tickets)
```

The `memory_usage` function returns the list of memory usage over a time interval. So we get the maximum value to measure:

```python
memory = max(memory_usage(insert_tickets))
```

Total memory usage of a function can be calculated by: the memory result minus the initial memory (`41.7 MiB`).

### 2. The `regenerate` command

### Version 1

```python
def regenerate_tokens():
    """The normal way to update batch of data
    """
    tickets = Ticket.objects.all()
    for t in tickets:
        t.token = uuid4()

    Ticket.objects.bulk_update(tickets, ["token"])
```

The main task can be done by that if we don't have a huge data collection.

Right after we loop through first ticket, django will get all data from Ticket table and cache it to `tickets` variable.

Therefore system try to save 1,000,000 data rows into memory. Then the process will be killed when it exceeded its container's memory limit:

```bash
root@ee2f26ee92c6:/code# python manage.py ticket --regenerate
Killed
```

So we need to use other method to loop through the data set without cache all data to memory.

### Version 2

The problem can be solved by using `Iterator`

```python
def regenerate_tokens_v2():
    """The optimized version of regenerate_tokens to reduce the memory usage by using iterator
    """
    chunk_size = 1000
    tickets = Ticket.objects.iterator(chunk_size=chunk_size)
    
    chunk = []
    for i, t in enumerate(tickets):
        t.token = uuid4()
        chunk.append(t)

        if (i+1) % chunk_size == 0:
            # update data by chunk when chunk_size reaches 1000
            Ticket.objects.bulk_update(chunk, ["token"])
            chunk = []
    
    # update remaining records if exist
    if chunk:
        Ticket.objects.bulk_update(chunk, ["token"])
```

For this version, query results will be streamed from the database using server-side cursors, since we're using PostgreSQL.
The data collection is no longer cached.

Memory measurement:

```bash
root@17f7194db6ef:/code# python manage.py ticket --regenerate2
Memory usage: 49.2852 MiB
Took: 219.6394 sec
```

Then the function took about `7.5 MiB`

`Iterator` is good for this case because we need to evaluate QuerySet only 1 time.

If we use `Iterator` on a QuerySet which has already been evaluated, then will force it to evaluate again, repeating the query.

### Showing progress

The progress is calculated after updating each `chunk_size` of data.

```python
total = Ticket.objects.count()
...
if (i+1) % chunk_size == 0:
    ...
    progress = (i + 1) / total * 100
    ...
```

### Estimates remaining time

The estimated remaining time is calculated based on processing time of each `chunk_size` of data.

```python
total = Ticket.objects.count()
...
if i % chunk_size == 0:
    # start timer
    start = timeit.default_timer()
    ...
if (i+1) % chunk_size == 0:
    ...
    # estimate remain time
    took = timeit.default_timer() - start
    estimated_remain_time = (total - i) / chunk_size * took

```

It will not have high accuracy at start, because the processing time of each `chunk_size` is not the same.
Anyway, it's an estimation.

We have an issue here. The `estimated_remain_time` is constantly changing. It can be greater than or less than the previous value.

So for a better experience, only show the remaining time when it becomes smaller

```python
display_remain_time = 999999
...
# avoid the display_remain_time keep fluctuating too much
if estimated_remain_time < display_remain_time:
    display_remain_time = estimated_remain_time
```

Then display these value by using `stdout`

```python
# print out status
self.stdout.write(
    "Progress: {:.1f}%".format(progress), ending=" "
)
self.stdout.write(
    "Remain: {:.0f}s".format(display_remain_time), ending="\r"
)
self.stdout.flush()
```

`flush` is used for replace the output. Then the result can be displayed on only one row.

```bash
Progress: 52.6% Remain: 132s
```

The Remain time was displayed as laggy as the estimated time of the downloading progress.

### Downside

This version covered almost the requirements, except save and continue the progress.
By using `Iterator`, we could know where the process is interrupted, but it's hard to continue from the point of interruption without looping through all data.

### Version 3

Track the progress by using `Paginator`

```python
def regenerate_tokens_v3():
    """The optimized version of regenerate_tokens to reduce the memory usage by using Paginator
    """
    tickets = Ticket.objects.all()
    paginator = Paginator(tickets, 1000)
        
    for i in paginator.page_range:        
        page = paginator.page(i)
        chunk = []
        
        for ticket in page.object_list:
            ticket.token = uuid4()
            chunk.append(ticket)
    
        Ticket.objects.bulk_update(chunk, ["token"])
```

This version is cleaner and can use the page number to save and continue the progress.

```python
error_output = "./error.log"
current_page = 1
...
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
    ...
    total_pages = paginator.num_pages
    for i in range(current_page, total_pages+1):
        ...
except (Exception, KeyboardInterrupt) as e:
    self.stdout.write(self.style.ERROR(str(e)))
    # write current_page to error output
    with open(error_output, "w") as f:
        f.write(str(current_page))
```

Test it

```bash
root@17f7194db6ef:/code# python manage.py ticket --regenerate3
Memory usage: 48.9766 MiB
Took: 370.2947 sec
```

This version took about `7.2 MiB`.
Compared with version 2, it took a smaller amount of memory but took longer execution time.

### Interruption testing

```bash
root@17f7194db6ef:/code# python manage.py ticket --regenerate3
^Cogress: 19.9% Remain: 189s
Process MemTimer-1:
Traceback (most recent call last):
  File "/usr/local/lib/python3.8/multiprocessing/process.py", line 315, in _bootstrap
    self.run()
  File "/usr/local/lib/python3.8/site-packages/memory_profiler.py", line 262, in run
    stop = self.pipe.poll(self.interval)
  File "/usr/local/lib/python3.8/multiprocessing/connection.py", line 257, in poll
    return self._poll(timeout)
  File "/usr/local/lib/python3.8/multiprocessing/connection.py", line 424, in _poll
    r = wait([self], timeout)
  File "/usr/local/lib/python3.8/multiprocessing/connection.py", line 931, in wait
    ready = selector.select(timeout)
  File "/usr/local/lib/python3.8/selectors.py", line 415, in select
    fd_event_list = self._selector.poll(timeout)
KeyboardInterrupt
```

File `error.log` was created and contains `200` inside.

Run command again

```bash
root@17f7194db6ef:/code# python manage.py ticket --regenerate3
Progress: 20.0% Remain: 205s
```

### Improvement

Tried to use multi-threading to update Django model. It's not success yet.
Since the command was executed inside container, the limitation of resources such as memory, cpu made multi-threading
code useless. It even increases the execution time.
Or maybe used an un-optimized number of threads.
