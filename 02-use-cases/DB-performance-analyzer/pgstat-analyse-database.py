
import json
import boto3
import psycopg2
import os
from botocore.exceptions import ClientError

def get_secret(secret_name):
    """Get secret from AWS Secrets Manager """
    #secret_name = os.environ['SECRET_NAME']
    region_name = os.environ['REGION']
    
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        secret_value = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(secret_value['SecretString'])
        return secret
    except ClientError as e:
        raise Exception(f"Failed to get secret: {str(e)}")

def execute_slow_query(secret_name, min_exec_time):
    """Execute multiple performance-related queries"""
    queries = {
        "slow_queries": """
            SELECT 
                CASE 
                    WHEN rolname IS NULL THEN 'unknown'
                    ELSE rolname 
                END as username,
                CASE 
                    WHEN datname IS NULL THEN 'unknown'
                    ELSE datname 
                END as database,
                query,
                calls,
                total_exec_time/1000 as total_time_sec,
                min_exec_time/1000 as min_time_sec,
                max_exec_time/1000 as max_time_sec,
                mean_exec_time/1000 as avg_time_sec,
                stddev_exec_time/1000 as stddev_time_sec,
                rows
            FROM pg_stat_statements s
            LEFT JOIN pg_roles r ON r.oid = s.userid
            LEFT JOIN pg_database d ON d.oid = s.dbid
            ORDER BY total_exec_time DESC
            LIMIT 10;
        """,
        "high_io_queries": """
            SELECT 
                CASE 
                    WHEN rolname IS NULL THEN 'unknown'
                    ELSE rolname 
                END as username,
                CASE 
                    WHEN datname IS NULL THEN 'unknown'
                    ELSE datname 
                END as database,
                query,
                shared_blks_hit,
                shared_blks_read,
                shared_blks_dirtied,
                shared_blks_written,
                local_blks_hit,
                local_blks_read,
                temp_blks_read,
                temp_blks_written
            FROM pg_stat_statements s
            LEFT JOIN pg_roles r ON r.oid = s.userid
            LEFT JOIN pg_database d ON d.oid = s.dbid
            ORDER BY shared_blks_read + shared_blks_written DESC
            LIMIT 5;
        """,
        "high_temp_queries": """
            SELECT 
                CASE 
                    WHEN rolname IS NULL THEN 'unknown'
                    ELSE rolname 
                END as username,
                CASE 
                    WHEN datname IS NULL THEN 'unknown'
                    ELSE datname 
                END as database,
                query,
                temp_blks_read,
                temp_blks_written
            FROM pg_stat_statements s
            LEFT JOIN pg_roles r ON r.oid = s.userid
            LEFT JOIN pg_database d ON d.oid = s.dbid
            ORDER BY temp_blks_written + temp_blks_read DESC
            LIMIT 5;
        """,
        "blocking_queries": """
            SELECT 
                blocked.pid AS blocked_pid,
                blocked.usename AS blocked_user,
                blocking.pid AS blocking_pid,
                blocking.usename AS blocking_user,
                blocked.query AS blocked_query,
                blocking.query AS blocking_query
            FROM pg_stat_activity blocked
            JOIN pg_stat_activity blocking ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
            WHERE NOT blocked.pid = blocking.pid
            LIMIT 3;;
        """
    }
    
    print("Connecting to the database...")
    conn = connect_to_db(secret_name)
    print("Connected to the database.")
    
    try:
        # First, ensure pg_stat_statements is installed
        print(" I am here 1")
        with conn.cursor() as cur:
            print(" I am here 2")
            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
            """)
            conn.commit()
        print(" I am here 3") 
        # Execute the main query
        
        results = {}
        # Execute each query and collect results
        for query_name, query in queries.items():
            print(" I am here 4")
            with conn.cursor() as cur:
                print(" I am here 5")
                cur.execute(query)
                print(" I am here 6")
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                results[query_name] = [dict(zip(columns, row)) for row in rows]
            print(" I am here 7")
        return results
            
    except Exception as e:
        raise Exception(f"Failed to retrieve slow queries: {str(e)}")
    finally:
        if conn:
            conn.close()

def format_results_for_slow_query(results):
    """Format results in a human-readable string"""
    output = "Database Performance Analysis Report\n\n"
    # Format slow queries
    output += "=== TOP 20 SLOW QUERIES ===\n"
    if results.get("slow_queries"):
        for idx, query in enumerate(results["slow_queries"], 1):
            output += f"\nQuery #{idx}:\n"
            output += f"• Username: {query['username']}\n"
            output += f"• Database: {query['database']}\n"
            output += f"• Calls: {query['calls']}\n"
            output += f"• Total Time: {round(query['total_time_sec'], 2)} sec\n"
            output += f"• Avg Time: {round(query['avg_time_sec'], 2)} sec\n"
            output += f"• Min Time: {round(query['min_time_sec'], 2)} sec\n"
            output += f"• Max Time: {round(query['max_time_sec'], 2)} sec\n"
            output += f"• Rows: {query['rows']}\n"
            output += f"• Query: {query['query']}\n"
    else:
        output += "No slow queries found.\n"
    
    # Format high IO queries
    output += "\n=== TOP 10 HIGH I/O QUERIES ===\n"
    if results.get("high_io_queries"):
        for idx, query in enumerate(results["high_io_queries"], 1):
            output += f"\nQuery #{idx}:\n"
            output += f"• Username: {query['username']}\n"
            output += f"• Database: {query['database']}\n"
            output += f"• Shared Blocks Hit: {query['shared_blks_hit']}\n"
            output += f"• Shared Blocks Read: {query['shared_blks_read']}\n"
            output += f"• Shared Blocks Written: {query['shared_blks_written']}\n"
            output += f"• Temp Blocks Read: {query['temp_blks_read']}\n"
            output += f"• Temp Blocks Written: {query['temp_blks_written']}\n"
            output += f"• Query: {query['query']}\n"
    else:
        output += "No high I/O queries found.\n"
    
    # Format high temp usage queries
    output += "\n=== TOP 10 HIGH TEMP USAGE QUERIES ===\n"
    if results.get("high_temp_queries"):
        for idx, query in enumerate(results["high_temp_queries"], 1):
            output += f"\nQuery #{idx}:\n"
            output += f"• Username: {query['username']}\n"
            output += f"• Database: {query['database']}\n"
            output += f"• Temp Blocks Read: {query['temp_blks_read']}\n"
            output += f"• Temp Blocks Written: {query['temp_blks_written']}\n"
            output += f"• Query: {query['query']}\n"
    else:
        output += "No high temp usage queries found.\n"
    
    # Format blocking queries
    output += "\n=== BLOCKING QUERIES ===\n"
    if results.get("blocking_queries"):
        for idx, query in enumerate(results["blocking_queries"], 1):
            output += f"\nBlocking Situation #{idx}:\n"
            output += f"• Blocked PID: {query['blocked_pid']}\n"
            output += f"• Blocked User: {query['blocked_user']}\n"
            output += f"• Blocked Query: {query['blocked_query']}\n"
            output += f"• Blocking PID: {query['blocking_pid']}\n"
            output += f"• Blocking User: {query['blocking_user']}\n"
            output += f"• Blocking Query: {query['blocking_query']}\n"
    else:
        output += "No blocking queries found.\n"
    return output

def execute_connect_issues(secret_name, min_exec_time):
    """Execute connection management related queries"""
    queries = {
        "current_connections": """
            SELECT 
                datname as database,
                usename as username,
                application_name,
                client_addr,
                backend_start,
                state,
                wait_event_type,
                wait_event,
                query
            FROM pg_stat_activity
            WHERE state IS NOT NULL
            ORDER BY backend_start DESC;
        """,
        "connection_stats": """
            SELECT 
                datname as database,
                numbackends as current_connections,
                xact_commit as commits,
                xact_rollback as rollbacks,
                blks_read,
                blks_hit,
                tup_returned,
                tup_fetched,
                tup_inserted,
                tup_updated,
                tup_deleted
            FROM pg_stat_database
            WHERE datname IS NOT NULL;
        """,
        "idle_connections": """
            SELECT 
                datname as database,
                usename as username,
                application_name,
                client_addr,
                backend_start,
                state,
                state_change,
                query
            FROM pg_stat_activity
            WHERE state = 'idle'
            ORDER BY backend_start DESC;
        """,
        "locked_queries": """
            SELECT DISTINCT ON (pid)
                pid,
                usename as username,
                datname as database,
                mode,
                CASE locktype
                    WHEN 'relation' THEN rel.relname
                    WHEN 'virtualxid' THEN 'virtual transaction'
                    WHEN 'transactionid' THEN 'transaction'
                    WHEN 'tuple' THEN 'tuple'
                    ELSE locktype
                END as lock_type,
                application_name,
                state,
                query,
                age(now(), query_start) as query_duration
            FROM pg_stat_activity sa
            JOIN pg_locks locks ON sa.pid = locks.pid
            LEFT JOIN pg_class rel ON rel.oid = locks.relation
            WHERE NOT granted
            ORDER BY pid, query_start;
        """
    }
    
    conn = connect_to_db(secret_name)
    try:
        # First, ensure pg_stat_statements is installed
        
        with conn.cursor() as cur:
            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
            """)
            conn.commit()
            
        # Execute the main query
        
        results = {}
        
        # Execute each query and collect results
        for query_name, query in queries.items():
            
            try:
                with conn.cursor() as cur:
                    
                    cur.execute(query)
                   
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    results[query_name] = [dict(zip(columns, row)) for row in rows]
                 
            except Exception as e:
                print(f"Error executing {query_name}: {str(e)}")
                results[query_name] = []
                
        return results
            
    except Exception as e:
        raise Exception(f"Failed to retrieve connection metrics: {str(e)}")
    finally:
        if conn:
            conn.close()

def format_results_for_conn_issues(results):
    """Format connection management results in a human-readable string"""
    output = "Database Connection Management Analysis Report\n\n"
    
    # Format current connections
    output += "=== CURRENT CONNECTIONS ===\n"
    if results.get("current_connections"):
        for idx, conn in enumerate(results["current_connections"], 1):
            output += f"\nConnection #{idx}:\n"
            output += f"• Database: {conn['database']}\n"
            output += f"• Username: {conn['username']}\n"
            output += f"• Application: {conn['application_name']}\n"
            output += f"• Client Address: {conn['client_addr']}\n"
            output += f"• State: {conn['state']}\n"
            output += f"• Wait Event Type: {conn['wait_event_type']}\n"
            output += f"• Wait Event: {conn['wait_event']}\n"
            output += f"• Current Query: {conn['query']}\n"
    else:
        output += "No current connections found.\n"
    
    # Format connection stats
    output += "\n=== DATABASE CONNECTION STATISTICS ===\n"
    if results.get("connection_stats"):
        for idx, stat in enumerate(results["connection_stats"], 1):
            output += f"\nDatabase: {stat['database']}\n"
            output += f"• Current Connections: {stat['current_connections']}\n"
            output += f"• Commits: {stat['commits']}\n"
            output += f"• Rollbacks: {stat['rollbacks']}\n"
            output += f"• Blocks Read: {stat['blks_read']}\n"
            output += f"• Blocks Hit: {stat['blks_hit']}\n"
            output += f"• Tuples Returned: {stat['tup_returned']}\n"
            output += f"• Tuples Fetched: {stat['tup_fetched']}\n"
            output += f"• Tuples Inserted: {stat['tup_inserted']}\n"
            output += f"• Tuples Updated: {stat['tup_updated']}\n"
            output += f"• Tuples Deleted: {stat['tup_deleted']}\n"
    else:
        output += "No connection statistics available.\n"
    
    # Format idle connections
    output += "\n=== IDLE CONNECTIONS ===\n"
    if results.get("idle_connections"):
        for idx, idle in enumerate(results["idle_connections"], 1):
            output += f"\nIdle Connection #{idx}:\n"
            output += f"• Database: {idle['database']}\n"
            output += f"• Username: {idle['username']}\n"
            output += f"• Application: {idle['application_name']}\n"
            output += f"• Client Address: {idle['client_addr']}\n"
            output += f"• Backend Start: {idle['backend_start']}\n"
            output += f"• State Change: {idle['state_change']}\n"
            output += f"• Last Query: {idle['query']}\n"
    else:
        output += "No idle connections found.\n"
    
    # Format locked queries
    output += "\n=== LOCKED QUERIES ===\n"
    if results.get("locked_queries"):
        for idx, lock in enumerate(results["locked_queries"], 1):
            output += f"\nLocked Query #{idx}:\n"
            output += f"• PID: {lock['pid']}\n"
            output += f"• Username: {lock['username']}\n"
            output += f"• Database: {lock['database']}\n"
            output += f"• Lock Type: {lock['lock_type']}\n"
            output += f"• Lock Mode: {lock['mode']}\n"
            output += f"• Application: {lock['application_name']}\n"
            output += f"• State: {lock['state']}\n"
            output += f"• Query Duration: {lock['query_duration']}\n"
            output += f"• Query: {lock['query']}\n"
    else:
        output += "No locked queries found.\n"
    
    return output

def execute_index_analysis(secret_name):
    """Execute index-related analysis queries"""
    queries = {
        "unused_indexes": """
            SELECT s.schemaname, 
                   s.relname as table_name, 
                   s.indexrelname as index_name, 
                   s.idx_scan, 
                   pg_size_pretty(pg_relation_size(s.indexrelid::regclass)) as index_size,
                   pg_relation_size(s.indexrelid) as index_size_bytes
            FROM pg_stat_user_indexes s
            JOIN pg_index i ON s.indexrelid = i.indexrelid
            WHERE s.idx_scan = 0 AND NOT i.indisprimary
            ORDER BY pg_relation_size(s.indexrelid) DESC;
        """,
        "missing_indexes": """
            SELECT schemaname, 
                   relname as table_name, 
                   seq_scan, 
                   seq_tup_read,
                   idx_scan, 
                   idx_tup_fetch,
                   pg_size_pretty(pg_relation_size(relid)) as table_size,
                   ROUND(seq_scan::float/(seq_scan+idx_scan+1)::float, 2) as seq_scan_ratio
            FROM pg_stat_user_tables
            WHERE seq_scan > 0
            ORDER BY seq_tup_read DESC;
        """,
        "index_efficiency": """
            SELECT s.relname as table_name,
                   i.indexrelname as index_name,
                   i.idx_scan as times_used,
                   pg_size_pretty(pg_relation_size(i.indexrelid::regclass)) as index_size,
                   ROUND(i.idx_scan::float / NULLIF(pg_relation_size(i.indexrelid), 0)::float, 6) as scans_per_byte
            FROM pg_stat_user_tables s
            JOIN pg_stat_user_indexes i ON s.relid = i.relid
            WHERE i.idx_scan > 0
            ORDER BY i.idx_scan::float / NULLIF(pg_relation_size(i.indexrelid), 0)::float ASC
            LIMIT 20;
        """
    }
    
    conn = connect_to_db(secret_name)
    try:
        # First, ensure pg_stat_statements is installed
        
        with conn.cursor() as cur:
            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
            """)
            conn.commit()
            
        # Execute the main query    
        results = {}
        
        # Execute each query and collect results
        for query_name, query in queries.items():
            try:
                with conn.cursor() as cur:
                    cur.execute(query)
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    results[query_name] = [dict(zip(columns, row)) for row in rows]
            except Exception as e:
                print(f"Error executing {query_name}: {str(e)}")
                results[query_name] = []
                
        return results
            
    except Exception as e:
        raise Exception(f"Failed to retrieve index metrics: {str(e)}")
    finally:
        if conn:
            conn.close()
    
def format_results_for_index_analysis(results):
    """Format index analysis results in a human-readable string"""
    output = "Database Index Analysis Report\n\n"
    
    # Format unused indexes
    output += "=== UNUSED INDEXES ===\n"
    if results.get("unused_indexes"):
        for idx, index in enumerate(results["unused_indexes"], 1):
            output += f"\nUnused Index #{idx}:\n"
            output += f"• Schema: {index['schemaname']}\n"
            output += f"• Table: {index['table_name']}\n"
            output += f"• Index: {index['index_name']}\n"
            output += f"• Scan Count: {index['idx_scan']}\n"
            output += f"• Index Size: {index['index_size']}\n"
        output += "\nRecommendation: Consider removing these unused indexes to reduce maintenance overhead and storage space.\n"
    else:
        output += "No unused indexes found.\n"
    
    # Format missing indexes
    output += "\n=== POTENTIAL MISSING INDEXES (High Sequential Scans) ===\n"
    if results.get("missing_indexes"):
        for idx, table in enumerate(results["missing_indexes"], 1):
            output += f"\nTable #{idx}:\n"
            output += f"• Schema: {table['schemaname']}\n"
            output += f"• Table: {table['table_name']}\n"
            output += f"• Sequential Scans: {table['seq_scan']}\n"
            output += f"• Sequential Tuples Read: {table['seq_tup_read']}\n"
            output += f"• Index Scans: {table['idx_scan']}\n"
            output += f"• Index Tuples Fetched: {table['idx_tup_fetch']}\n"
            output += f"• Table Size: {table['table_size']}\n"
            output += f"• Sequential Scan Ratio: {table['seq_scan_ratio']}\n"
        output += "\nRecommendation: Tables with high sequential scan ratios might benefit from additional indexes.\n"
    else:
        output += "No tables with significant sequential scans found.\n"
    
    # Format index efficiency
    output += "\n=== INDEX USAGE EFFICIENCY ===\n"
    if results.get("index_efficiency"):
        for idx, index in enumerate(results["index_efficiency"], 1):
            output += f"\nIndex #{idx}:\n"
            output += f"• Table: {index['table_name']}\n"
            output += f"• Index: {index['index_name']}\n"
            output += f"• Times Used: {index['times_used']}\n"
            output += f"• Index Size: {index['index_size']}\n"
            output += f"• Scans per Byte: {index['scans_per_byte']}\n"
        output += "\nRecommendation: Indexes with very low scans per byte might be candidates for removal or restructuring.\n"
    else:
        output += "No index usage statistics found.\n"
    
    return output

def execute_autovacuum_analysis(secret_name):
    """Execute autovacuum-related analysis queries"""
    queries = {
        "tables_needing_vacuum": """
            SELECT relname as table_name, 
                   n_dead_tup as dead_tuples, 
                   n_live_tup as live_tuples, 
                   (n_dead_tup::float / NULLIF(n_live_tup + n_dead_tup, 0) * 100)::numeric(10,2) as dead_percentage,
                   last_vacuum,
                   last_autovacuum,
                   last_analyze,
                   last_autoanalyze
            FROM pg_stat_user_tables
            WHERE n_dead_tup > 0
            ORDER BY dead_percentage DESC;
        """,
        "autovacuum_activity": """
            SELECT pid, 
                   datname, 
                   usename, 
                   query, 
                   state, 
                   wait_event_type, 
                   wait_event, 
                   age(now(), xact_start) as xact_age,
                   age(now(), query_start) as query_age
            FROM pg_stat_activity
            WHERE query LIKE '%autovacuum%' 
            AND state != 'idle';
        """,
        "table_bloat": """
            SELECT schemaname, 
                   relname, 
                   n_live_tup, 
                   n_dead_tup, 
                   pg_size_pretty(pg_total_relation_size(schemaname || '.' || relname::text)) as total_size
            FROM pg_stat_user_tables
            ORDER BY n_dead_tup DESC
            LIMIT 20;
        """,
        "wraparound_status": """
            SELECT datname, 
                   age(datfrozenxid) as xid_age,
                   current_setting('autovacuum_freeze_max_age')::int as max_age,
                   round(100 * age(datfrozenxid)::float / 
                   current_setting('autovacuum_freeze_max_age')::int) as percent_towards_wraparound
            FROM pg_database
            ORDER BY age(datfrozenxid) DESC;
        """
    }
    
    conn = connect_to_db(secret_name)
    try:
        # First, ensure pg_stat_statements is installed
        
        with conn.cursor() as cur:
            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
            """)
            conn.commit()
            
        # Execute the main query    
        results = {}
        
        # Execute each query and collect results
        for query_name, query in queries.items():
            try:
                with conn.cursor() as cur:
                    cur.execute(query)
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    results[query_name] = [dict(zip(columns, row)) for row in rows]
            except Exception as e:
                print(f"Error executing {query_name}: {str(e)}")
                results[query_name] = []
                
        return results
            
    except Exception as e:
        raise Exception(f"Failed to retrieve autovacuum metrics: {str(e)}")
    finally:
        if conn:
            conn.close()

def format_results_for_autovacuum_analysis(results):
    """Format autovacuum analysis results in a human-readable string"""
    output = "Database Autovacuum Analysis Report\n\n"
    
    # Format tables needing vacuum
    output += "=== TABLES NEEDING VACUUM ===\n"
    if results.get("tables_needing_vacuum"):
        for idx, table in enumerate(results["tables_needing_vacuum"], 1):
            output += f"\nTable #{idx}:\n"
            output += f"• Table Name: {table['table_name']}\n"
            output += f"• Dead Tuples: {table['dead_tuples']}\n"
            output += f"• Live Tuples: {table['live_tuples']}\n"
            output += f"• Dead Percentage: {table['dead_percentage']}%\n"
            output += f"• Last Vacuum: {table['last_vacuum'] or 'Never'}\n"
            output += f"• Last Autovacuum: {table['last_autovacuum'] or 'Never'}\n"
            output += f"• Last Analyze: {table['last_analyze'] or 'Never'}\n"
            output += f"• Last Autoanalyze: {table['last_autoanalyze'] or 'Never'}\n"
        output += "\nRecommendation: Consider running VACUUM on tables with high dead tuple percentages.\n"
    else:
        output += "No tables with dead tuples found.\n"
    
    # Format current autovacuum activity
    output += "\n=== CURRENT AUTOVACUUM ACTIVITY ===\n"
    if results.get("autovacuum_activity"):
        for idx, activity in enumerate(results["autovacuum_activity"], 1):
            output += f"\nAutovacuum Process #{idx}:\n"
            output += f"• PID: {activity['pid']}\n"
            output += f"• Database: {activity['datname']}\n"
            output += f"• User: {activity['usename']}\n"
            output += f"• State: {activity['state']}\n"
            output += f"• Wait Event Type: {activity['wait_event_type']}\n"
            output += f"• Wait Event: {activity['wait_event']}\n"
            output += f"• Transaction Age: {activity['xact_age']}\n"
            output += f"• Query Age: {activity['query_age']}\n"
            output += f"• Query: {activity['query']}\n"
    else:
        output += "No active autovacuum processes found.\n"
    
    # Format table bloat information
    output += "\n=== TABLE BLOAT INFORMATION ===\n"
    if results.get("table_bloat"):
        for idx, bloat in enumerate(results["table_bloat"], 1):
            output += f"\nTable #{idx}:\n"
            output += f"• Schema: {bloat['schemaname']}\n"
            output += f"• Table: {bloat['relname']}\n"
            output += f"• Live Tuples: {bloat['n_live_tup']}\n"
            output += f"• Dead Tuples: {bloat['n_dead_tup']}\n"
            output += f"• Total Size: {bloat['total_size']}\n"
    else:
        output += "No table bloat information available.\n"
    
    # Format transaction wraparound status
    output += "\n=== TRANSACTION WRAPAROUND STATUS ===\n"
    if results.get("wraparound_status"):
        for idx, status in enumerate(results["wraparound_status"], 1):
            output += f"\nDatabase: {status['datname']}\n"
            output += f"• XID Age: {status['xid_age']}\n"
            output += f"• Max Age: {status['max_age']}\n"
            output += f"• Percent Towards Wraparound: {status['percent_towards_wraparound']}%\n"
            
            # Add warning if approaching wraparound
            if status['percent_towards_wraparound'] > 75:
                output += "⚠️ WARNING: Database is approaching transaction wraparound limit!\n"
    else:
        output += "No wraparound status information available.\n"
    
    return output

def execute_io_analysis(secret_name):
    """Execute I/O-related analysis queries"""
    queries = {
        "buffer_usage": """
            SELECT relname as table_name, 
                   heap_blks_read, 
                   heap_blks_hit,
                   CASE WHEN heap_blks_read + heap_blks_hit > 0 
                        THEN (heap_blks_hit::float / (heap_blks_read + heap_blks_hit) * 100)::numeric(10,2) 
                        ELSE 0 
                   END as hit_percentage
            FROM pg_statio_user_tables
            ORDER BY heap_blks_read DESC;
        """,
        "checkpoint_activity": """
            SELECT checkpoints_timed, 
                   checkpoints_req, 
                   checkpoint_write_time, 
                   checkpoint_sync_time,
                   buffers_checkpoint, 
                   buffers_clean, 
                   buffers_backend, 
                   buffers_backend_fsync,
                   buffers_alloc, 
                   stats_reset
            FROM pg_stat_bgwriter;
        """,
        "io_statistics": """
            SELECT s.relname as table_name,
                   pg_size_pretty(pg_relation_size(s.relid)) as table_size,
                   io.heap_blks_read, 
                   io.heap_blks_hit,
                   io.idx_blks_read, 
                   io.idx_blks_hit,
                   io.toast_blks_read, 
                   io.toast_blks_hit,
                   io.tidx_blks_read, 
                   io.tidx_blks_hit
            FROM pg_statio_user_tables io
            JOIN pg_stat_user_tables s ON io.relid = s.relid
            ORDER BY (io.heap_blks_read + io.idx_blks_read + 
                     io.toast_blks_read + io.tidx_blks_read) DESC
            LIMIT 20;
        """
    }
    
    conn = connect_to_db(secret_name)
    try:
        # First, ensure pg_stat_statements is installed
        
        with conn.cursor() as cur:
            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
            """)
            conn.commit()
        
        results = {}
        
        # Execute each query and collect results
        for query_name, query in queries.items():
            try:
                with conn.cursor() as cur:
                    cur.execute(query)
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    results[query_name] = [dict(zip(columns, row)) for row in rows]
            except Exception as e:
                print(f"Error executing {query_name}: {str(e)}")
                results[query_name] = []
                
        return results
            
    except Exception as e:
        raise Exception(f"Failed to retrieve I/O metrics: {str(e)}")
    finally:
        if conn:
            conn.close()

def format_results_for_io_analysis(results):
    """Format I/O analysis results in a human-readable string"""
    output = "Database I/O Analysis Report\n\n"
    
    # Format buffer usage
    output += "=== BUFFER USAGE BY TABLE ===\n"
    if results.get("buffer_usage"):
        for idx, table in enumerate(results["buffer_usage"], 1):
            output += f"\nTable #{idx}:\n"
            output += f"• Table Name: {table['table_name']}\n"
            output += f"• Blocks Read from Disk: {table['heap_blks_read']}\n"
            output += f"• Blocks Hit in Buffer: {table['heap_blks_hit']}\n"
            output += f"• Buffer Hit Percentage: {table['hit_percentage']}%\n"
            
            # Add recommendations based on hit percentage
            if table['hit_percentage'] < 90:
                output += "⚠️ Warning: Low buffer hit ratio. Consider increasing shared_buffers.\n"
    else:
        output += "No buffer usage statistics available.\n"
    
    # Format checkpoint activity
    output += "\n=== CHECKPOINT ACTIVITY ===\n"
    if results.get("checkpoint_activity") and results["checkpoint_activity"]:
        checkpoint = results["checkpoint_activity"][0]  # Should only be one row
        output += f"• Scheduled Checkpoints: {checkpoint['checkpoints_timed']}\n"
        output += f"• Requested Checkpoints: {checkpoint['checkpoints_req']}\n"
        output += f"• Checkpoint Write Time: {checkpoint['checkpoint_write_time']} ms\n"
        output += f"• Checkpoint Sync Time: {checkpoint['checkpoint_sync_time']} ms\n"
        output += f"• Buffers Written During Checkpoints: {checkpoint['buffers_checkpoint']}\n"
        output += f"• Buffers Written by Background Writer: {checkpoint['buffers_clean']}\n"
        output += f"• Buffers Written by Backend Processes: {checkpoint['buffers_backend']}\n"
        output += f"• Backend fsync Calls: {checkpoint['buffers_backend_fsync']}\n"
        output += f"• Buffers Allocated: {checkpoint['buffers_alloc']}\n"
        output += f"• Statistics Reset Time: {checkpoint['stats_reset']}\n"
        
        # Add recommendations based on checkpoint activity
        if checkpoint['checkpoints_req'] > checkpoint['checkpoints_timed']:
            output += "\n⚠️ Warning: High number of requested checkpoints. Consider increasing checkpoint_timeout or max_wal_size.\n"
    else:
        output += "No checkpoint activity information available.\n"
    
    # Format I/O statistics
    output += "\n=== DETAILED I/O STATISTICS (TOP 20 TABLES) ===\n"
    if results.get("io_statistics"):
        for idx, stat in enumerate(results["io_statistics"], 1):
            output += f"\nTable #{idx}:\n"
            output += f"• Table Name: {stat['table_name']}\n"
            output += f"• Table Size: {stat['table_size']}\n"
            output += f"• Heap Blocks Read: {stat['heap_blks_read']}\n"
            output += f"• Heap Blocks Hit: {stat['heap_blks_hit']}\n"
            output += f"• Index Blocks Read: {stat['idx_blks_read']}\n"
            output += f"• Index Blocks Hit: {stat['idx_blks_hit']}\n"
            output += f"• Toast Blocks Read: {stat['toast_blks_read']}\n"
            output += f"• Toast Blocks Hit: {stat['toast_blks_hit']}\n"
            output += f"• Toast Index Blocks Read: {stat['tidx_blks_read']}\n"
            output += f"• Toast Index Blocks Hit: {stat['tidx_blks_hit']}\n"
            
            # Calculate and show hit ratios
            total_reads = stat['heap_blks_read'] + stat['idx_blks_read']
            total_hits = stat['heap_blks_hit'] + stat['idx_blks_hit']
            if total_reads + total_hits > 0:
                hit_ratio = (total_hits / (total_reads + total_hits)) * 100
                output += f"• Overall Buffer Hit Ratio: {hit_ratio:.2f}%\n"
                if hit_ratio < 90:
                    output += "⚠️ Warning: Low buffer hit ratio for this table.\n"
    else:
        output += "No I/O statistics available.\n"
    
    return output

def execute_replication_analysis(secret_name):
    """Execute replication-related analysis queries"""
    queries = {
        "aurora_replica_status": """
            SELECT server_id, 
                   EXTRACT(EPOCH FROM (now() - last_update_timestamp)) AS lag_seconds,
                   durable_lsn,
                   highest_lsn_rcvd,
                   current_read_lsn,
                   last_update_timestamp
            FROM aurora_replica_status;
        """,
        "replication_slots": """
            SELECT slot_name, 
                   slot_type, 
                   active, 
                   confirmed_flush_lsn, 
                   pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)) as lag_size
            FROM pg_replication_slots;
        """,
        "replication_connections": """
            SELECT pid, 
                   usesysid, 
                   usename, 
                   application_name, 
                   client_addr, 
                   client_hostname, 
                   client_port, 
                   backend_start, 
                   state, 
                   sent_lsn, 
                   write_lsn, 
                   flush_lsn, 
                   replay_lsn,
                   pg_wal_lsn_diff(sent_lsn, replay_lsn) as lag_bytes
            FROM pg_stat_replication;
        """
    }
    
    conn = connect_to_db(secret_name)
    try:
        # First, ensure pg_stat_statements is installed
        
        with conn.cursor() as cur:
            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
            """)
            conn.commit()
        results = {}
        
        # Execute each query and collect results
        for query_name, query in queries.items():
            try:
                with conn.cursor() as cur:
                    cur.execute(query)
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    results[query_name] = [dict(zip(columns, row)) for row in rows]
            except Exception as e:
                print(f"Error executing {query_name}: {str(e)}")
                results[query_name] = []
                
        return results
            
    except Exception as e:
        raise Exception(f"Failed to retrieve replication metrics: {str(e)}")
    finally:
        if conn:
            conn.close()

def format_results_for_replication_analysis(results):
    """Format replication analysis results in a human-readable string"""
    output = "Database Replication Analysis Report\n\n"
    
    # Format Aurora replica status
    output += "=== AURORA REPLICA STATUS ===\n"
    if results.get("aurora_replica_status"):
        for idx, replica in enumerate(results["aurora_replica_status"], 1):
            output += f"\nReplica #{idx}:\n"
            output += f"• Server ID: {replica['server_id']}\n"
            output += f"• Replication Lag: {round(float(replica['lag_seconds']), 2)} seconds\n"
            output += f"• Durable LSN: {replica['durable_lsn']}\n"
            output += f"• Highest Received LSN: {replica['highest_lsn_rcvd']}\n"
            output += f"• Current Read LSN: {replica['current_read_lsn']}\n"
            output += f"• Last Update: {replica['last_update_timestamp']}\n"
            
            # Add warnings for high lag
            if float(replica['lag_seconds']) > 30:
                output += "⚠️ Warning: High replication lag detected!\n"
    else:
        output += "No Aurora replica status information available.\n"
    
    # Format replication slots
    output += "\n=== REPLICATION SLOTS ===\n"
    if results.get("replication_slots"):
        for idx, slot in enumerate(results["replication_slots"], 1):
            output += f"\nSlot #{idx}:\n"
            output += f"• Slot Name: {slot['slot_name']}\n"
            output += f"• Slot Type: {slot['slot_type']}\n"
            output += f"• Active: {slot['active']}\n"
            output += f"• Confirmed Flush LSN: {slot['confirmed_flush_lsn']}\n"
            output += f"• Lag Size: {slot['lag_size']}\n"
            
            # Add warnings for inactive slots
            if not slot['active']:
                output += "⚠️ Warning: Inactive replication slot detected!\n"
    else:
        output += "No replication slots found.\n"
    
    # Format replication connections
    output += "\n=== REPLICATION CONNECTIONS ===\n"
    if results.get("replication_connections"):
        for idx, conn in enumerate(results["replication_connections"], 1):
            output += f"\nConnection #{idx}:\n"
            output += f"• PID: {conn['pid']}\n"
            output += f"• Username: {conn['usename']}\n"
            output += f"• Application: {conn['application_name']}\n"
            output += f"• Client Address: {conn['client_addr']}\n"
            output += f"• Client Hostname: {conn['client_hostname']}\n"
            output += f"• Client Port: {conn['client_port']}\n"
            output += f"• Backend Start: {conn['backend_start']}\n"
            output += f"• State: {conn['state']}\n"
            output += f"• Sent LSN: {conn['sent_lsn']}\n"
            output += f"• Write LSN: {conn['write_lsn']}\n"
            output += f"• Flush LSN: {conn['flush_lsn']}\n"
            output += f"• Replay LSN: {conn['replay_lsn']}\n"
            output += f"• Lag Size: {conn['lag_bytes']} bytes\n"
            
            # Add warnings for large lag
            if conn['lag_bytes'] > 100000000:  # 100MB
                output += "⚠️ Warning: Large replication lag detected!\n"
    else:
        output += "No replication connections found.\n"
    
    return output

def execute_system_health(secret_name):
    """Execute system health-related analysis queries"""
    queries = {
        "database_statistics": """
            SELECT datname, 
                   numbackends, 
                   xact_commit, 
                   xact_rollback, 
                   blks_read, 
                   blks_hit, 
                   tup_returned, 
                   tup_fetched, 
                   tup_inserted, 
                   tup_updated, 
                   tup_deleted,
                   conflicts, 
                   temp_files, 
                   temp_bytes, 
                   deadlocks, 
                   blk_read_time, 
                   blk_write_time,
                   stats_reset
            FROM pg_stat_database
            WHERE datname = current_database();
        """,
        "lock_contention": """
            SELECT locktype, 
                   CASE 
                       WHEN relation IS NOT NULL THEN relation::regclass::text 
                       ELSE 'NULL'
                   END as relation,
                   mode, 
                   transactionid as tid,
                   virtualtransaction as vtid, 
                   pid, 
                   granted
            FROM pg_locks
            ORDER BY relation;
        """,
        "long_running_transactions": """
            SELECT pid, 
                   usename, 
                   datname, 
                   age(now(), xact_start) as xact_age, 
                   state, 
                   query
            FROM pg_stat_activity 
            WHERE state != 'idle' 
            AND xact_start < now() - interval '5 minutes'
            ORDER BY xact_start;
        """
    }
    
    conn = connect_to_db(secret_name)
    try:
        # First, ensure pg_stat_statements is installed
        
        with conn.cursor() as cur:
            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
            """)
            conn.commit()
        
        results = {}
        
        # Execute each query and collect results
        for query_name, query in queries.items():
            try:
                with conn.cursor() as cur:
                    cur.execute(query)
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    results[query_name] = [dict(zip(columns, row)) for row in rows]
            except Exception as e:
                print(f"Error executing {query_name}: {str(e)}")
                results[query_name] = []
                
        return results
            
    except Exception as e:
        raise Exception(f"Failed to retrieve system health metrics: {str(e)}")
    finally:
        if conn:
            conn.close()

def format_results_for_system_health(results):
    """Format system health analysis results in a human-readable string"""
    output = "Database System Health Report\n\n"
    
    # Format database statistics
    output += "=== DATABASE STATISTICS ===\n"
    if results.get("database_statistics"):
        for stat in results["database_statistics"]:
            output += f"Database: {stat['datname']}\n"
            output += f"• Active Connections: {stat['numbackends']}\n"
            output += f"• Transactions Committed: {stat['xact_commit']}\n"
            output += f"• Transactions Rolled Back: {stat['xact_rollback']}\n"
            output += f"• Blocks Read: {stat['blks_read']}\n"
            output += f"• Blocks Hit (Cache): {stat['blks_hit']}\n"
            
            # Calculate cache hit ratio
            total_blocks = stat['blks_read'] + stat['blks_hit']
            if total_blocks > 0:
                cache_hit_ratio = (stat['blks_hit'] / total_blocks) * 100
                output += f"• Cache Hit Ratio: {cache_hit_ratio:.2f}%\n"
                if cache_hit_ratio < 90:
                    output += "⚠️ Warning: Low cache hit ratio. Consider increasing shared_buffers.\n"
            
            output += f"• Tuples Returned: {stat['tup_returned']}\n"
            output += f"• Tuples Fetched: {stat['tup_fetched']}\n"
            output += f"• Tuples Inserted: {stat['tup_inserted']}\n"
            output += f"• Tuples Updated: {stat['tup_updated']}\n"
            output += f"• Tuples Deleted: {stat['tup_deleted']}\n"
            output += f"• Conflicts: {stat['conflicts']}\n"
            output += f"• Temporary Files Created: {stat['temp_files']}\n"
            output += f"• Temporary Bytes Written: {stat['temp_bytes']}\n"
            output += f"• Deadlocks: {stat['deadlocks']}\n"
            output += f"• Block Read Time: {stat['blk_read_time']} ms\n"
            output += f"• Block Write Time: {stat['blk_write_time']} ms\n"
            output += f"• Statistics Reset: {stat['stats_reset']}\n"
            
            # Add warnings for concerning metrics
            if stat['deadlocks'] > 0:
                output += "⚠️ Warning: Deadlocks detected!\n"
            if stat['conflicts'] > 0:
                output += "⚠️ Warning: Conflicts detected!\n"
            if stat['temp_files'] > 1000:
                output += "⚠️ Warning: High number of temporary files created!\n"
    else:
        output += "No database statistics available.\n"
    
    # Format lock contention
    output += "\n=== LOCK CONTENTION ===\n"
    if results.get("lock_contention"):
        lock_groups = {}
        for lock in results["lock_contention"]:
            relation = lock['relation']
            if relation not in lock_groups:
                lock_groups[relation] = []
            lock_groups[relation].append(lock)
        
        for relation, locks in lock_groups.items():
            output += f"\nRelation: {relation}\n"
            for idx, lock in enumerate(locks, 1):
                output += f"Lock #{idx}:\n"
                output += f"• Type: {lock['locktype']}\n"
                output += f"• Mode: {lock['mode']}\n"
                output += f"• Transaction ID: {lock['tid']}\n"
                output += f"• Virtual Transaction ID: {lock['vtid']}\n"
                output += f"• PID: {lock['pid']}\n"
                output += f"• Granted: {lock['granted']}\n"
                
                if not lock['granted']:
                    output += "⚠️ Warning: Lock waiting to be granted!\n"
    else:
        output += "No lock contention found.\n"
    
    # Format long-running transactions
    output += "\n=== LONG-RUNNING TRANSACTIONS (> 5 minutes) ===\n"
    if results.get("long_running_transactions"):
        for idx, txn in enumerate(results["long_running_transactions"], 1):
            output += f"\nTransaction #{idx}:\n"
            output += f"• PID: {txn['pid']}\n"
            output += f"• Username: {txn['usename']}\n"
            output += f"• Database: {txn['datname']}\n"
            output += f"• Age: {txn['xact_age']}\n"
            output += f"• State: {txn['state']}\n"
            output += f"• Query: {txn['query']}\n"
            
            # Add warning for very long-running transactions
            if 'hours' in str(txn['xact_age']) or 'days' in str(txn['xact_age']):
                output += "⚠️ Warning: Transaction running for an extended period!\n"
    else:
        output += "No long-running transactions found.\n"
    
    return output

def connect_to_db(secret_name):
    """Establish database connection"""
    cur_secret = secret_name
    secret = get_secret(cur_secret)
    print(secret)
    try:
        print("in connect_to_db")
        conn = psycopg2.connect(
            host=secret['host'],
            database=secret['dbname'],
            user=secret['username'],
            password=secret['password'],
            port=secret['port']
        )
        return conn
    except Exception as e:
        raise Exception(f"Failed to connect to the database: {str(e)}")

def get_env_secret(environment):
    ssm_client = boto3.client('ssm')
    print("in get_env_secret")
    """Retrieve the secret name for the specified environment"""
    if environment == 'prod':
        print("in get_env_secret1")
        try:
            # Get the secret name from Parameter Store
            print("in get_env_secret-try")
            response = ssm_client.get_parameter(
                Name=f'/AuroraOpsGPT/{environment}'
            )
            print(response['Parameter']['Value'])
            return response['Parameter']['Value']
        except ssm_client.exceptions.ParameterNotFound:
            error_message = f"Parameter not found: {parameter_name}"
            print(error_message)
            raise Exception(error_message)
    elif environment == 'dev':
        try:
            # Get the secret name from Parameter Store
            response = ssm_client.get_parameter(
                Name=f'/AuroraOpsGPT/{environment}'
            )
            return response['Parameter']['Value']
        except Exception as e:
            raise Exception(f"Failed to get dev secret name from Parameter Store: {str(e)}")
    else:
        print("environement does not exist")
        raise ValueError(f"Unknown environment: {environment}")

def lambda_handler(event, context):
    try:
        print(event)
        environment = event['environment']
        action_type = event['action_type']
        print("Environment: {}".format(environment))
        secret_name = get_env_secret(environment)
        min_exec_time = 1000
        print(event)
        # Get slow queries
        #if tool_name == 'slow_query':
        if action_type == 'slow_query':
            print("Executing slow query scripts")
            results = execute_slow_query(secret_name, min_exec_time)
            # Format results for Bedrock Agent
            formatted_output = format_results_for_slow_query(results)
            print(formatted_output)
        elif action_type == 'connection_management_issues':
            print("Executing connection_management_issues")
            results = execute_connect_issues(secret_name, min_exec_time)
            # Format results for Bedrock Agent
            formatted_output = format_results_for_conn_issues(results)
        elif action_type == 'index_analysis':
            print("Executing index_analysis")
            results = execute_index_analysis(secret_name)
            formatted_output = format_results_for_index_analysis(results)
        elif action_type == 'autovacuum_analysis':
            print("Executing autovacuum_analysis")
            results = execute_autovacuum_analysis(secret_name)
            formatted_output = format_results_for_autovacuum_analysis(results)
        elif action_type == 'io_analysis':
            print("Executing io_analysis")
            results = execute_io_analysis(secret_name)
            formatted_output = format_results_for_io_analysis(results)
        elif action_type == 'replication_analysis':
            print("Executing replication_analysis")
            results = execute_replication_analysis(secret_name)
            formatted_output = format_results_for_replication_analysis(results)
        elif action_type == 'system_health':
            print("Executing system_health")
            results = execute_system_health(secret_name)
            formatted_output = format_results_for_system_health(results)
        else:
            return {
                "functionResponse": {
                    "content": f"Error: Unknown "
                }
            }

        response_body = {
        'TEXT': {
            'body': formatted_output
            }
        }

        function_response = {
        'functionResponse': {
            'responseBody': response_body
            }
        }
       
        
        return function_response

    except Exception as e:
        return json.dumps({
            "functionResponse": {
                "content": f"Error analyzing slow queries: {str(e)}"
            }
        })