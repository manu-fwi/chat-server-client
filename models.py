from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, aliased
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from db_base import Base

class db_clientchannel(Base):
    __tablename__= "clientchannel"
    id = Column(Integer, primary_key=True)
    client_id = Column(ForeignKey('clients.id'))
    channel_id = Column(ForeignKey('channels.id'))
    creation = Column(DateTime(),index=True)
    deletion = Column(DateTime,index=True)
    channel = relationship('db_channel',foreign_keys=channel_id,
                           back_populates = 'joined_clients')
    client = relationship('db_client',foreign_keys=client_id,
                          back_populates = 'joined_channels')

class db_msgtochannel(Base):
    __tablename__= "msgtochannel"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer,ForeignKey('clients.id'))
    channel_id = Column(Integer,ForeignKey('channels.id'))
    message = Column(String(300))
    creation = Column(DateTime(),index=True)
    channel = relationship('db_channel',foreign_keys=channel_id,
                           back_populates = 'sending_clients')
    client = relationship('db_client',foreign_keys=client_id,
                          back_populates = 'msgs_sent_to_channels')


class db_client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    nickname = Column(String(64), index=True)
    address = Column(String(120), index=True)
    connection = Column(DateTime())
    deconnection = Column(DateTime())
    channels = relationship('db_channel', backref='client')
    joined_channels = relationship('db_clientchannel',
                                   back_populates='client')
    msgs_sent_to_channels = relationship('db_msgtochannel',
                                         back_populates='client')

    def __repr__(self):
        return '<Client id={}, channels=, {} at {}>'.format(self.id,self.nickname,self.address)

class db_msgtoclient(Base):
    __tablename__= "msgtoclient"
    id = Column(Integer, primary_key=True)
    from_client_id = Column(Integer,ForeignKey('clients.id'))
    from_client = relationship(db_client,backref="msgs_sent_to_clients",
                               primaryjoin=(db_client.id == from_client_id))
    to_client_id = Column(Integer,ForeignKey('clients.id'))
    to_client = relationship(db_client,backref="msgs_rcv_from_clients",
                               primaryjoin=(db_client.id == to_client_id))
    message = Column(String(300))
    creation = Column(DateTime(),index=True)

    def __repr__(self):
        return '<msg={}, from {} at {}>'.format(self.message,
                                                self.from_client_id,
                                                self.to_client_id)

class db_channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), index=True)
    creator = Column(Integer,ForeignKey('clients.id'))
    creation = Column(DateTime())
    deletion = Column(DateTime())
    joined_clients = relationship('db_clientchannel',
                                  back_populates='channel')
    sending_clients = relationship('db_msgtochannel',
                                   back_populates='channel')
    

    def __repr__(self):
        return '<Channel id={}, {} created by {}>'.format(self.id,self.name,self.creator)


def connect_to_db(filename,echo = True):
    Base = declarative_base()    
    engine = create_engine('sqlite:///'+filename, echo=echo)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session

"""
if __name__ == "__main__":
    engine,Session = connect_to_db("app.db", True)
    while True:
        sending_cl_name = input("sending client? ")
        if sending_cl_name == "stop":
            break
        with Session() as session:
            sending_cl = session.query(db_client).filter_by(nickname=sending_cl_name).first()

            rcv = input("to? ")
            if rcv[0]=="#":
                to_channel = True
                rcv_end = session.query(db_channel).filter_by(name=rcv).first()
            else:
                rcv_end = session.query(db_client).filter_by(nickname=rcv).first()
                to_channel = False

            msg = input("msg? ")

            if to_channel:
                session.add(db_msgtochannel(client_id=sending_cl.id,channel_id=rcv_end.id,message=msg,creation=datetime.utcnow()))
            else:
                session.add(db_msgtoclient(from_client_id=sending_cl.id,to_client_id=rcv_end.id,message=msg,creation=datetime.utcnow()))
            if to_channel:
                print(sending_cl.msgs_sent_to_channels)
                print(rcv_end.sending_clients)
            else:
                print(sending_cl.msgs_sent_to_clients)
                print(rcv_end.msgs_rcv_from_clients)
            session.commit()
"""
