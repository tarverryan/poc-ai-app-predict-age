# Lessons Learned

This document captures authentic learning experiences from building this AWS serverless ML pipeline. These are real insights from working through the challenges and trade-offs.

## What Worked Well

### Step Functions Orchestration
Step Functions proved to be an excellent choice for orchestrating the pipeline. The visual workflow, built-in retry logic, and native AWS integration made it much simpler than managing a custom orchestrator. The Map state for parallel execution was particularly powerful – it automatically handles scaling, error handling, and retries for hundreds of parallel tasks.

### Parquet Optimization
Switching from JSON to Parquet format with Snappy compression had a massive impact on Athena query costs. The columnar format and compression significantly reduced the amount of data scanned, making the pipeline much more cost-effective. This was one of the most impactful optimizations.

### Infrastructure as Code with Terraform
Using Terraform for all infrastructure made it easy to reproduce the entire stack, version control changes, and understand the complete architecture. The modular structure (separate files for Lambda, Fargate, Step Functions) made it maintainable.

### VPC Endpoints for Cost Optimization
Configuring VPC endpoints for ECR, S3, and CloudWatch Logs eliminated data transfer costs and improved security. This was a simple change that had both cost and security benefits.

## What Surprised Me

### Step Functions 256KB Output Limit
I hit an unexpected limitation when using Step Functions Map state with many parallel tasks. The combined output exceeded the 256KB limit, causing failures. The solution was using `ResultPath = null` to discard outputs, but this required understanding Step Functions internals better than I initially expected.

### ARM64 Capacity Constraints
I initially chose ARM64 for Fargate tasks because it's cheaper, but ran into capacity constraints when trying to launch hundreds of parallel tasks. Switching to X86_64 solved the availability issue, even though it cost more. This taught me that capacity availability can be more important than raw cost per unit.

### Athena CTAS Performance
Athena's CTAS (Create Table As Select) operations were much faster than I expected for large datasets. The ability to do feature engineering directly in SQL and write Parquet files to S3 in one operation was a game-changer. However, I learned to be careful with query complexity – some queries that worked on small datasets failed on large ones.

### Lambda Timeout vs Fargate Cost Trade-off
The 15-minute Lambda timeout forced me to use Fargate for training, which initially seemed like overkill. But after benchmarking, I realized Fargate was actually the right choice – the training job needed more time and resources than Lambda could provide, and the cost difference wasn't as significant as I feared.

## Trade-offs Discovered

### Lambda vs Fargate for Batch Jobs
**Lambda:** Great for short tasks (<15 min), automatic scaling, pay-per-invocation. But timeout limits and memory constraints make it unsuitable for longer ML workloads.

**Fargate:** More expensive per hour, but no timeout limits, more memory/CPU options, and better for long-running compute-intensive tasks.

**Decision:** Use Lambda for orchestration and short data prep tasks, Fargate for training and batch prediction.

### Athena Scan Costs vs Query Performance
Athena charges per TB scanned, so optimizing queries to scan less data directly reduces costs. Parquet compression, columnar storage, and partitioning all help, but require upfront work to set up properly.

**Trade-off:** More time spent optimizing data format = significantly lower query costs. Worth it for repeated queries.

### Step Functions vs Custom Orchestrator
**Step Functions:** Native AWS integration, built-in retries, visual workflow, pay-per-state-transition. But less flexible than custom code, and has some limitations (like the 256KB output limit).

**Custom Orchestrator:** More control, can handle any use case. But you're responsible for retries, error handling, monitoring, and scaling.

**Decision:** Step Functions for this use case – the benefits outweighed the limitations.

### Parallelism vs Cost
More parallel tasks = faster completion but higher cost. Finding the right balance requires understanding your cost constraints and time requirements.

**Learning:** Start with lower parallelism, measure costs, then increase if needed. Don't assume maximum parallelism is always best.

## What I'd Improve Next

### Monitoring and Observability
I'd add more comprehensive monitoring – custom CloudWatch metrics, dashboards, and alerts. The current setup has basic logging, but more visibility into pipeline health, costs, and performance would be valuable.

### Testing Strategy
I'd add automated tests for the Lambda functions and containerized components. Unit tests for data transformations, integration tests for the pipeline stages, and end-to-end tests with synthetic data would make the pipeline more reliable.

### Cost Optimization
I'd explore more cost optimization strategies:
- Spot instances for Fargate (if available)
- More aggressive S3 lifecycle policies
- Query result caching in Athena
- Right-sizing Fargate tasks more precisely

### Error Recovery
I'd improve error recovery – currently if a stage fails, you need to manually investigate and potentially re-run. Better error messages, automatic retry with exponential backoff, and partial failure handling would make the pipeline more resilient.

### Documentation
I'd add more inline code documentation and examples. While the architecture docs are good, more code-level comments explaining "why" decisions were made would help others understand the implementation.

### Local Development
I'd set up LocalStack or similar for local testing. Currently, you need an AWS account to test, which makes development slower and more expensive.

## Key Takeaways

1. **Serverless doesn't mean "no infrastructure thinking"** – You still need to understand capacity, costs, and trade-offs.

2. **Data format matters a lot** – Parquet compression was one of the biggest cost wins, but required upfront work.

3. **Step Functions is powerful but has limits** – Understanding those limits (like output size) is crucial.

4. **Cost optimization is iterative** – Start simple, measure, then optimize based on actual usage patterns.

5. **Infrastructure as Code is essential** – Terraform made it possible to iterate quickly and understand the full stack.

6. **Trade-offs are everywhere** – Every architectural decision involves balancing cost, performance, complexity, and operational overhead.

---

**Last Updated:** January 2025  
**Author:** Ryan Tarver

