# Ticket Puzzle

A database table/model "Ticket" has 1 million rows. The table has a "token" column that holds a random unique UUID value for each row, determined by Django/Python logic at the time of creation.

Due to a data leak, the candidate should write a django management command to iterate over every Ticket record to regenerate the unique UUID value.

The command should inform the user of progress as the script runs and estimates the amount of time remaining.

The script should also be sensitive to the potentially limited amount of server memory and avoid loading the full dataset into memory all at once, and show an understanding of Django ORM memory usage and query execution.

Finally, the script should ensure that if it is interrupted that it should save progress and restart near the point of interruption so that it does not need to process the entire table from the start.

Please use Django / Python for your solution. The logic and thought process demonstrated are the most important considerations rather than truly functional code, however code presentation is important as well as the technical aspect. If you cannot settle on a single perfect solution, you may also discuss alternative solutions to demonstrate your understanding of potential trade-offs as you encounter them. Of course if you consider a solution is too time consuming you are also welcome to clarify or elaborate on potential improvements or multiple solution approaches conceptually to demonstrate understanding and planned solution.
