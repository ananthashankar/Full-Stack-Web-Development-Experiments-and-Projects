#!/usr/bin/env python
#
# tournament.py -- implementation of a Swiss-system tournament
#

import psycopg2


def connect():
    """Connect to the PostgreSQL database.  Returns a database connection."""
    return psycopg2.connect("dbname=tournament")


def deleteMatches():
    """Remove all the match records from the database."""
    conn=connect()
    c=conn.cursor()
    c.execute("Delete from matches")
    conn.commit()
    conn.close()



def deletePlayers():
    """Remove all the player records from the database."""
    conn=connect()
    c=conn.cursor()
    c.execute("Delete from players")
    conn.commit()
    conn.close()


def countPlayers():
    """Returns the number of players currently registered."""
    conn=connect()
    c=conn.cursor()
    c.execute("Select count(*) from players")
    num  = c.fetchone()
    conn.close()
    return int(num[0])


def registerPlayer(name):
    """Adds a player to the tournament database.
        
        The database assigns a unique serial id number for the player.  (This
        should be handled by your SQL database schema, not in your Python code.)
        
        Args:
        name: the player's full name (need not be unique).
        """
    conn=connect()
    c=conn.cursor()
    c.execute("Insert into players (name, matchesPlayed, wins, loss, points, byes) values (%s, 0, 0, 0, 0, 0)", (name,))
    conn.commit()
    conn.close()


def playerStandings():
    """Returns a list of the players and their win records, sorted by wins.
        
        The first entry in the list should be the player in first place, or a player
        tied for first place if there is currently a tie.
        
        Returns:
        A list of tuples, each of which contains (id, name, wins, matches):
        id: the player's unique id (assigned by the database)
        name: the player's full name (as registered)
        wins: the number of matches the player has won
        matches: the number of matches the player has played
        """
    
    conn=connect()
    c=conn.cursor()
    c.execute("Select id, name, wins, matchesPlayed from players order by points")
    res = list(c.fetchall())
    cnt = 0
    while(cnt < len(res)):
        if(cnt < len(res)-1):
            row = res[cnt]
            tmp = res[cnt+1]
            #Checking whether the next player has same wins
            if(int(row[2])==int(tmp[2])):
                c.execute("Select sum(wins) from players where id in(Select player1 from matches where player2 = %s)", (int(row[0]),))
                tmp1 = c.fetchone()
                tmp4 = int(tmp1[0])
                c.execute("Select sum(wins) from players where id in(Select player2 from matches where player1 = %s)", (int(row[0]),))
                tmp1 = c.fetchone()
                tmp4 = tmp4 + int(tmp1[0])
                c.execute("Select sum(wins) from players where id in(Select player1 from matches where player2 = %s)", (int(tmp[0]),))
                tmp1 = c.fetchone()
                tmp2 = int(tmp1[0])
                c.execute("Select sum(wins) from players where id in(Select player2 from matches where player1 = %s)", (int(tmp[0]),))
                tmp1 = c.fetchone()
                tmp2 = tmp2 + int(tmp1[0])
                #Checking whose Opponent Match Wins is greater
                if(tmp2 > tmp4):
                    #Exchanging the ranks if the latter player has better profile by OMW ratings
                    tmp3 = res[cnt + 1]
                    res[cnt + 1] = res[cnt]
                    res[cnt] = tmp3
        cnt = cnt + 1;
    
    conn.close()
    return res


def reportMatch(winner, loser, tie_flag):
    """Records the outcome of a single match between two players.
        
        Args:
        winner:  the id number of the player who won
        loser:  the id number of the player who lost
        if tie_flag == 1 then both players will get 1 points else winner will get 2 points
        """
    conn=connect()
    c=conn.cursor()
    c.execute("Select matchesPlayed, wins, loss, points from players where id = %s", (winner,))
    res = c.fetchone()
    match_num = int(res[0]) + 1
    win_num = int(res[1]) + 1
    loss_num = int(res[2])
    pnt_num = int(res[3]) + 2
    if(tie_flag==1):
        win_num = win_num - 1
        pnt_num = pnt_num - 1
    
    win_num = int(res[1]) + 1
    c.execute("Update players Set wins=%s, matchesPlayed=%s, loss=%s, points=%s where id = %s", (win_num, match_num, loss_num, pnt_num, winner,))
    conn.commit()
    c.execute("Select matchesPlayed, wins, loss, points from players where id = %s", (loser,))
    res = c.fetchone()
    match_num = int(res[0]) + 1
    win_num = int(res[1])
    loss_num = int(res[2]) + 1
    pnt_num = int(res[3])
    if(tie_flag==1):
        loss_num = loss_num - 1
        pnt_num = pnt_num + 1
    
    c.execute("Update players Set loss=%s, matchesPlayed=%s loss=%s, points=%s where id = %s", (loss_num, match_num,  loss_num, pnt_num, loser,))
    #Updating match results in matches table
    if(tie_flag!=1):
        c.execute("Update matches set winner=%s, loser=%s where (player1 = %s AND player2 = %s AND winner = 0 AND loser = 0) OR (player1 = %s AND player2 = %s AND winner = 0 AND loser = 0)", (winner, loser, winner, loser, loser, winner,))
    conn.commit()
    conn.close()


def swissPairings():
    """Returns a list of pairs of players for the next round of a match.
        
        Assuming that there are an even number of players registered, each player
        appears exactly once in the pairings.  Each player is paired with another
        player with an equal or nearly-equal win record, that is, a player adjacent
        to him or her in the standings.
        
        Returns:
        A list of tuples, each of which contains (id1, name1, id2, name2)
        id1: the first player's unique id
        name1: the first player's name
        id2: the second player's unique id
        name2: the second player's name
        """
    
    conn=connect()
    c=conn.cursor()
    c.execute("Select id, name from players order by points")
    res  = list(c.fetchall())
    #Assigning byes to unassigned player if odd number of players are registered in a tournament
    if(len(res)%2!=0):
        c.execute("Select id from players where byes = 0 order by points")
        tmp = list(c.fetchall())
        cnt = 0
        c.execute("Select points from players where id=%s", (int(tmp[0]),))
        tmp1 = c.fetchone();
        pnts = int(tmp1[0]) + 2;
        c.execute("Update players set byes=1, points=%s where id=%s", (pnts,int(tmp[0]),))
        while(cnt < len(res)):
            row = res[cnt]
            if(int(row[0]) == int(tmp[0])):
                del res[cnt]
                break
            cnt = cnt + 1

cnt = 0
    lngth = len(res)/2
    fin = []
    #run a loop for half the length of res and in nested loop check for previous matches pair to rule out once new pair is formed delete the pair from res and continue
    
    while(cnt < lngth):
        curr_row = res[0]
        tmp = 1
        lngth1 = len(res) - 1
        while(tmp <= lngth1):
            next_row = res[tmp]
            c.execute("Select count(*) from matches where (player1 = %s AND player2 = %s) OR (player1 = %s AND player2 = %s)", (int(curr_row[0]), int(next_row[0]), int(next_row[0]), int(curr_row[0]),))
            tmp1 = c.fetchone()
            if(int(tmp1[0])==0):
                break
            tmp = tmp + 1
        fin.append(tuple(res[0]) + tuple(res[tmp]))
        del res[0]
        del res[tmp]
        cnt = cnt + 1
    
    
    for sPair in fin:
        c.execute("Select max(round) from matches")
        rnd = c.fetchone()
        c.execute("Insert into matches (player1, player2, round, winner, loser) values (%s, %s, %s, 0, 0)", (int(spair[0]), int(spair[2]), int(rnd[0]),))
conn.close()
    return fin









