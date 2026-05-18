from src.conversations import Message


def test_sqlite_persists_order_without_duplicates(conversation_manager):
    conversation_manager.append(Message(role="user", content="uno"))
    conversation_manager.append(Message(role="assistant", content="dos"))
    conversation_manager.append(Message(role="user", content="tres"))

    reloaded = conversation_manager.store.load_all()
    conversation = next(iter(reloaded.values()))
    messages = conversation.messages

    assert [message.content for message in messages] == ["uno", "dos", "tres"]
    assert len({message.id for message in messages}) == 3
