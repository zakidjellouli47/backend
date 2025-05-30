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
    
    struct VoteDetail {
        address voter;
        uint256 candidateId;
        uint256 timestamp;
        string encryptedVoteProof; // For additional verification
    }
    
    // State variables
    uint256 private electionCounter;
    mapping(uint256 => Election) public elections;
    mapping(uint256 => mapping(uint256 => Candidate)) public candidates;
    mapping(uint256 => uint256) private candidateCounters;
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    mapping(uint256 => VoteDetail[]) public voteDetails; // Track complete vote history
    mapping(uint256 => uint256) public totalVotesPerElection;
    
    // Events
    event ElectionCreated(uint256 electionId, string title, address creator);
    event CandidateAdded(uint256 electionId, uint256 candidateId, string name);
    event VoteCast(uint256 electionId, uint256 candidateId, address voter);
    event ElectionResultsFinalized(uint256 electionId, uint256 totalVotes);
    
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

    // Enhanced Functions
    
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
        require(msg.sender == elections[electionId].creator, "Only election creator can add candidates");
        
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
    
    // Enhanced vote function with detailed tracking
    function vote(
        uint256 electionId,
        uint256 candidateId,
        string memory encryptedProof
    ) public 
      electionExists(electionId) 
      candidateExists(electionId, candidateId) 
      electionActive(electionId) 
      hasNotVoted(electionId) {
        
        // Update candidate vote count
        candidates[electionId][candidateId].voteCount++;
        
        // Record voter participation
        hasVoted[electionId][msg.sender] = true;
        
        // Store complete vote details
        voteDetails[electionId].push(VoteDetail({
            voter: msg.sender,
            candidateId: candidateId,
            timestamp: block.timestamp,
            encryptedVoteProof: encryptedProof
        }));
        
        // Update total votes
        totalVotesPerElection[electionId]++;
        
        emit VoteCast(electionId, candidateId, msg.sender);
        
        // Automatically finalize if election ended
        if (block.timestamp >= elections[electionId].endTime) {
            emit ElectionResultsFinalized(electionId, totalVotesPerElection[electionId]);
        }
    }
    
    // New query functions for dynamic voting
    
    function getVoterDetails(uint256 electionId, address voter) 
        public 
        view 
        electionExists(electionId) 
        returns (VoteDetail memory) 
    {
        for (uint i = 0; i < voteDetails[electionId].length; i++) {
            if (voteDetails[electionId][i].voter == voter) {
                return voteDetails[electionId][i];
            }
        }
        revert("Voter not found in this election");
    }
    
    function getAllVotes(uint256 electionId) 
        public 
        view 
        electionExists(electionId) 
        returns (VoteDetail[] memory) 
    {
        return voteDetails[electionId];
    }
    
    function getVotesByCandidate(uint256 electionId, uint256 candidateId)
        public
        view
        electionExists(electionId)
        candidateExists(electionId, candidateId)
        returns (VoteDetail[] memory)
    {
        uint256 count = 0;
        for (uint i = 0; i < voteDetails[electionId].length; i++) {
            if (voteDetails[electionId][i].candidateId == candidateId) {
                count++;
            }
        }
        
        VoteDetail[] memory result = new VoteDetail[](count);
        uint256 index = 0;
        for (uint i = 0; i < voteDetails[electionId].length; i++) {
            if (voteDetails[electionId][i].candidateId == candidateId) {
                result[index] = voteDetails[electionId][i];
                index++;
            }
        }
        return result;
    }
    
    // Original view functions with enhancements
    
    function getElection(uint256 electionId) public view electionExists(electionId) returns (
        uint256 id,
        string memory title,
        string memory description,
        uint256 startTime,
        uint256 endTime,
        address creator,
        uint256 totalVotes
    ) {
        Election memory election = elections[electionId];
        return (
            election.id,
            election.title,
            election.description,
            election.startTime,
            election.endTime,
            election.creator,
            totalVotesPerElection[electionId]
        );
    }
    
    function getCandidate(uint256 electionId, uint256 candidateId) public view 
      electionExists(electionId) 
      candidateExists(electionId, candidateId) 
      returns (
        uint256 id,
        string memory name,
        address candidateAddress,
        uint256 voteCount,
        uint256 percentageOfTotal
    ) {
        Candidate memory candidate = candidates[electionId][candidateId];
        uint256 total = totalVotesPerElection[electionId];
        uint256 percentage = total > 0 ? (candidate.voteCount * 100) / total : 0;
        
        return (
            candidate.id,
            candidate.name,
            candidate.candidateAddress,
            candidate.voteCount,
            percentage
        );
    }
    
    function getElectionResults(uint256 electionId) public view electionExists(electionId) returns (
        uint256[] memory candidateIds,
        string[] memory names,
        uint256[] memory voteCounts,
        uint256[] memory percentages,
        uint256 totalVotes
    ) {
        require(block.timestamp > elections[electionId].endTime, "Election has not ended yet");
        
        uint256 count = candidateCounters[electionId];
        candidateIds = new uint256[](count);
        names = new string[](count);
        voteCounts = new uint256[](count);
        percentages = new uint256[](count);
        totalVotes = totalVotesPerElection[electionId];
        
        for (uint256 i = 1; i <= count; i++) {
            candidateIds[i-1] = i;
            names[i-1] = candidates[electionId][i].name;
            voteCounts[i-1] = candidates[electionId][i].voteCount;
            percentages[i-1] = totalVotes > 0 ? (voteCounts[i-1] * 100) / totalVotes : 0;
        }
        
        return (candidateIds, names, voteCounts, percentages, totalVotes);
    }
}