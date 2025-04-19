// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VotingSystem {
    // Structures
    struct Election {
        uint256 id;
        string title;
        string description;
        uint256 startTime;
        uint256 endTime;
        address creator;
        bool exists;
    }
    
    struct Candidate {
        uint256 id;
        string name;
        address candidateAddress;
        uint256 voteCount;
        bool exists;
    }
    
    // State variables
    uint256 private electionCounter;
    mapping(uint256 => Election) private elections;
    mapping(uint256 => mapping(uint256 => Candidate)) private candidates;
    mapping(uint256 => uint256) private candidateCounters;
    mapping(uint256 => mapping(address => bool)) private hasVoted;
    
    // Events
    event ElectionCreated(uint256 electionId, string title, address creator);
    event CandidateAdded(uint256 electionId, uint256 candidateId, string name);
    event VoteCast(uint256 electionId, uint256 candidateId, address voter);
    
    // Modifiers
    modifier electionExists(uint256 electionId) {
        require(elections[electionId].exists, "Election does not exist");
        _;
    }
    
    modifier candidateExists(uint256 electionId, uint256 candidateId) {
        require(candidates[electionId][candidateId].exists, "Candidate does not exist");
        _;
    }
    
    modifier electionActive(uint256 electionId) {
        require(
            block.timestamp >= elections[electionId].startTime &&
            block.timestamp <= elections[electionId].endTime,
            "Election is not active"
        );
        _;
    }
    
    modifier hasNotVoted(uint256 electionId) {
        require(!hasVoted[electionId][msg.sender], "Already voted in this election");
        _;
    }
    
    // Functions
    function createElection(
        string memory title,
        string memory description,
        uint256 startTime,
        uint256 endTime
    ) public returns (uint256) {
        require(startTime < endTime, "End time must be after start time");
        require(startTime >= block.timestamp, "Start time cannot be in the past");
        
        electionCounter++;
        uint256 electionId = electionCounter;
        
        elections[electionId] = Election({
            id: electionId,
            title: title,
            description: description,
            startTime: startTime,
            endTime: endTime,
            creator: msg.sender,
            exists: true
        });
        
        candidateCounters[electionId] = 0;
        
        emit ElectionCreated(electionId, title, msg.sender);
        return electionId;
    }
    
    function addCandidate(
        uint256 electionId,
        address candidateAddress,
        string memory name
    ) public electionExists(electionId) returns (uint256) {
        require(block.timestamp < elections[electionId].startTime, "Election has already started");
        
        uint256 candidateId = candidateCounters[electionId] + 1;
        candidateCounters[electionId] = candidateId;
        
        candidates[electionId][candidateId] = Candidate({
            id: candidateId,
            name: name,
            candidateAddress: candidateAddress,
            voteCount: 0,
            exists: true
        });
        
        emit CandidateAdded(electionId, candidateId, name);
        return candidateId;
    }
    
    function vote(
        uint256 electionId,
        uint256 candidateId
    ) public 
      electionExists(electionId) 
      candidateExists(electionId, candidateId) 
      electionActive(electionId) 
      hasNotVoted(electionId) {
        
        // Record the vote
        candidates[electionId][candidateId].voteCount++;
        hasVoted[electionId][msg.sender] = true;
        
        emit VoteCast(electionId, candidateId, msg.sender);
    }
    
    // View functions
    function getElection(uint256 electionId) public view electionExists(electionId) returns (
        uint256 id,
        string memory title,
        string memory description,
        uint256 startTime,
        uint256 endTime,
        address creator
    ) {
        Election memory election = elections[electionId];
        return (
            election.id,
            election.title,
            election.description,
            election.startTime,
            election.endTime,
            election.creator
        );
    }
    
    function getCandidate(uint256 electionId, uint256 candidateId) public view 
      electionExists(electionId) 
      candidateExists(electionId, candidateId) returns (
        uint256 id,
        string memory name,
        address candidateAddress,
        uint256 voteCount
    ) {
        Candidate memory candidate = candidates[electionId][candidateId];
        return (
            candidate.id,
            candidate.name,
            candidate.candidateAddress,
            candidate.voteCount
        );
    }
    
    function getCandidateCount(uint256 electionId) public view electionExists(electionId) returns (uint256) {
        return candidateCounters[electionId];
    }
    
    function hasUserVoted(uint256 electionId, address user) public view electionExists(electionId) returns (bool) {
        return hasVoted[electionId][user];
    }
    
    function getElectionResults(uint256 electionId) public view electionExists(electionId) returns (
        uint256[] memory candidateIds,
        string[] memory names,
        uint256[] memory voteCounts
    ) {
        require(block.timestamp > elections[electionId].endTime, "Election has not ended yet");
        
        uint256 count = candidateCounters[electionId];
        candidateIds = new uint256[](count);
        names = new string[](count);
        voteCounts = new uint256[](count);
        
        for (uint256 i = 1; i <= count; i++) {
            candidateIds[i-1] = i;
            names[i-1] = candidates[electionId][i].name;
            voteCounts[i-1] = candidates[electionId][i].voteCount;
        }
        
        return (candidateIds, names, voteCounts);
    }
}