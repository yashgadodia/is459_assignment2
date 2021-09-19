import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, desc, monotonically_increasing_id
from graphframes import *

spark = SparkSession.builder.appName('sg.edu.smu.is459.assignment2').getOrCreate()

# Load data
posts_df = spark.read.load('/Users/yash/parquet-input/hardwarezone.parquet')
# posts_df = spark.read.load('/Users/yash/parquet-input/hardwarezone.parquet')
# posts_df = spark.read.load('/Users/yash/Google\ Drive/Yash/SMU/Y3S1/IS459/test/SMU-IS459/spark/hardwarezone.parquet')

# Clean the dataframe by removing rows with any null value
posts_df = posts_df.na.drop()

#posts_df.createOrReplaceTempView("posts")

# Find distinct users
#distinct_author = spark.sql("SELECT DISTINCT author FROM posts")
author_df = posts_df.select('author').distinct()

print('Author number :' + str(author_df.count()))

# Assign ID to the users
author_id = author_df.withColumn('id', monotonically_increasing_id())
author_id.show()

# Construct connection between post and author
left_df = posts_df.select('topic', 'author') \
    .withColumnRenamed("topic","ltopic") \
    .withColumnRenamed("author","src_author")

right_df =  left_df.withColumnRenamed('ltopic', 'rtopic') \
    .withColumnRenamed('src_author', 'dst_author')

#  Self join on topic to build connection between authors
author_to_author = left_df. \
    join(right_df, left_df.ltopic == right_df.rtopic) \
    .select(left_df.src_author, right_df.dst_author) \
    .distinct()
edge_num = author_to_author.count()
print('Number of edges with duplicate : ' + str(edge_num))

# Convert it into ids
id_to_author = author_to_author \
    .join(author_id, author_to_author.src_author == author_id.author) \
    .select(author_to_author.dst_author, author_id.id) \
    .withColumnRenamed('id','src')

id_to_id = id_to_author \
    .join(author_id, id_to_author.dst_author == author_id.author) \
    .select(id_to_author.src, author_id.id) \
    .withColumnRenamed('id', 'dst')

id_to_id = id_to_id.filter(id_to_id.src >= id_to_id.dst).distinct()

id_to_id.cache()

print("Number of edges without duplciate :" + str(id_to_id.count())) # show unique authors 

# Build graph with RDDs
graph = GraphFrame(author_id, id_to_id)

# For complex graph queries, e.g., connected components, you need to set
# the checkopoint directory on HDFS, so Spark can handle failures.
# Remember to change to a valid directory in your HDFS
spark.sparkContext.setCheckpointDir('/Users/yash/spark-checkpoint')

# The rest is your work, guys

# Question 1

result = graph.connectedComponents()
result.select("id", "component").orderBy("component").show() # assign each node a componenet id 
result.groupBy("component").count().sort(desc("count")).show()

# for stop words
from pyspark.ml.feature import StopWordsRemover
posts_rdd = posts_df.rdd
content_rdd = posts_rdd.map(lambda x: x[2].lower().split(' '))
words_rdd = content_rdd.map(lambda x: (x,1))
word_rdd = words_rdd.reduceByKey(lambda x, y: x+y)
word_rdd = word_rdd.sortBy(lambda pair:pair[1],ascending = False)
#to get list of stopwords
from pyspark.ml.feature import StopWordsRemover
remover = StopWordsRemover()
stopwords = remover.getStopWords()
stopwords.append('\n')
stopwords.append('')
stopwords.append('\ni')
#filter stopwords out and print top 10
filtered_words_rdd = word_rdd.filter(lambda x: x[0] not in stopwords)
filtered_words_rdd.take(10)

# Question 2 

results2 = graph.triangleCount()
results2.agg(avg("count")).show()



