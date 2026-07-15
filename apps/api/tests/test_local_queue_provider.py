from app.infrastructure.queue.local_queue_provider import LocalQueueProvider


def test_queue_preserves_fifo_order_and_peek_does_not_remove_jobs():
    provider = LocalQueueProvider[str]()
    provider.enqueue("first")
    provider.enqueue("second")

    assert provider.size() == 2
    assert provider.peek() == "first"
    assert provider.size() == 2
    assert provider.dequeue() == "first"
    assert provider.dequeue() == "second"
    assert provider.dequeue() is None


def test_queue_clear_removes_all_jobs():
    provider = LocalQueueProvider[int]()
    provider.enqueue(1)
    provider.enqueue(2)

    provider.clear()

    assert provider.peek() is None
    assert provider.size() == 0
